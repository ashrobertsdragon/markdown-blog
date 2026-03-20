"""Unit tests for handle_process_notifications.

Covers:
- Returns empty summary dict when no pending notifications
- Calls notification_repo.get_pending with command.batch_limit
- Calls email_sender.send with (recipient_email, event_type, variables)
- On successful send: calls mark_sent and increments sent count
- On None send result with attempts < max_retries: calls mark_for_retry
- On None send result with attempts >= max_retries: calls mark_failed
- Returns correct summary dict
- Catches per-notification exceptions and continues processing
- reply_received variables include REPLY_AUTHOR, POST_TITLE,
  REPLY_EXCERPT, UNSUBSCRIBE_URL
- comment_posted variables include REPLY_AUTHOR, POST_TITLE,
  ORIGINAL_COMMENT, UNSUBSCRIBE_URL
"""

from datetime import UTC, datetime
from unittest.mock import MagicMock

from backend.application.commands.handlers.process_notifications_handler import (  # noqa: E501
    handle_process_notifications,
)
from backend.application.commands.process_notifications_command import (
    ProcessNotificationsCommand,
)


def _make_command(
    *,
    batch_limit: int = 100,
    max_retries: int = 3,
) -> ProcessNotificationsCommand:
    """Build a ProcessNotificationsCommand."""
    return ProcessNotificationsCommand(
        batch_limit=batch_limit,
        max_retries=max_retries,
    )


def _make_notification(
    *,
    notification_id: int = 1,
    event_type: str = "reply_received",
    recipient_id: int = 10,
    sender_id: int = 5,
    post_id: int = 100,
    comment_id: int = 50,
    attempt_count: int = 0,
) -> MagicMock:
    """Build a mock Notification aggregate."""
    n = MagicMock()
    n.id = notification_id
    n.event_type = event_type
    n.recipient_id = recipient_id
    n.sender_id = sender_id
    n.post_id = post_id
    n.comment_id = comment_id
    n.attempt_count = attempt_count
    return n


def _make_user(email: str = "user@example.com") -> MagicMock:
    """Build a mock User."""
    user = MagicMock()
    user.email = email
    return user


def _make_post(title: str = "My Post") -> MagicMock:
    """Build a mock Post."""
    post = MagicMock()
    post.title = title
    return post


def _make_comment(text: str = "Original comment text") -> MagicMock:
    """Build a mock Comment."""
    comment = MagicMock()
    comment.text = text
    return comment


def _make_repos(
    notifications: list[MagicMock] | None = None,
    user: MagicMock | None = None,
    post: MagicMock | None = None,
    comment: MagicMock | None = None,
) -> tuple[MagicMock, MagicMock, MagicMock, MagicMock]:
    """Return (notification_repo, post_repo, comment_repo, user_repo) mocks."""
    notification_repo = MagicMock()
    notification_repo.get_pending.return_value = notifications or []

    post_repo = MagicMock()
    post_repo.find_by_id.return_value = post or _make_post()

    comment_repo = MagicMock()
    comment_repo.find_by_id.return_value = comment or _make_comment()

    user_repo = MagicMock()
    user_repo.find_by_id.return_value = user or _make_user()

    return notification_repo, post_repo, comment_repo, user_repo


def test_returns_empty_summary_when_no_pending() -> None:
    """Returns zero counts when no pending notifications exist."""
    cmd = _make_command()
    notification_repo, post_repo, comment_repo, user_repo = _make_repos()
    email_sender = MagicMock()

    result = handle_process_notifications(
        cmd, notification_repo, email_sender, post_repo, comment_repo, user_repo
    )

    assert result == {"sent": 0, "failed": 0, "total": 0}


def test_calls_get_pending_with_batch_limit() -> None:
    """notification_repo.get_pending is called with command.batch_limit."""
    cmd = _make_command(batch_limit=25)
    notification_repo, post_repo, comment_repo, user_repo = _make_repos()
    email_sender = MagicMock()

    handle_process_notifications(
        cmd, notification_repo, email_sender, post_repo, comment_repo, user_repo
    )

    notification_repo.get_pending.assert_called_once_with(25)


def test_calls_email_sender_with_recipient_email_and_event_type() -> None:
    """email_sender.send is called with recipient email and event_type."""
    notification = _make_notification(event_type="reply_received")
    user = _make_user(email="recipient@example.com")
    cmd = _make_command()
    notification_repo, post_repo, comment_repo, user_repo = _make_repos(
        notifications=[notification], user=user
    )
    email_sender = MagicMock()
    email_sender.send.return_value = "resend-id-123"

    handle_process_notifications(
        cmd, notification_repo, email_sender, post_repo, comment_repo, user_repo
    )

    call_args = email_sender.send.call_args
    assert call_args[0][0] == "recipient@example.com"
    assert call_args[0][1] == "reply_received"


def test_calls_mark_sent_on_successful_send() -> None:
    """mark_sent is called on the aggregate and repo.save persists it."""
    notification = _make_notification(notification_id=7)
    cmd = _make_command()
    notification_repo, post_repo, comment_repo, user_repo = _make_repos(
        notifications=[notification]
    )
    email_sender = MagicMock()
    email_sender.send.return_value = "resend-abc"

    handle_process_notifications(
        cmd, notification_repo, email_sender, post_repo, comment_repo, user_repo
    )

    notification.mark_sent.assert_called_once()
    notification_repo.save.assert_called_once_with(notification)


def test_increments_sent_count_on_success() -> None:
    """sent count increments for each successfully delivered notification."""
    notifications = [
        _make_notification(notification_id=1),
        _make_notification(notification_id=2),
    ]
    cmd = _make_command()
    notification_repo, post_repo, comment_repo, user_repo = _make_repos(
        notifications=notifications
    )
    email_sender = MagicMock()
    email_sender.send.return_value = "resend-id"

    result = handle_process_notifications(
        cmd, notification_repo, email_sender, post_repo, comment_repo, user_repo
    )

    assert result["sent"] == 2


def test_calls_mark_for_retry_when_send_fails_under_max_retries() -> None:
    """mark_for_retry is called when send returns None and attempts < max."""
    notification = _make_notification(notification_id=3, attempt_count=1)
    cmd = _make_command(max_retries=3)
    notification_repo, post_repo, comment_repo, user_repo = _make_repos(
        notifications=[notification]
    )
    email_sender = MagicMock()
    email_sender.send.return_value = None

    handle_process_notifications(
        cmd, notification_repo, email_sender, post_repo, comment_repo, user_repo
    )

    notification_repo.mark_for_retry.assert_called_once()
    call_args = notification_repo.mark_for_retry.call_args
    assert call_args[0][0] == 3


def test_does_not_call_mark_failed_when_retries_remain() -> None:
    """mark_failed is not called when attempts < max_retries."""
    notification = _make_notification(attempt_count=1)
    cmd = _make_command(max_retries=3)
    notification_repo, post_repo, comment_repo, user_repo = _make_repos(
        notifications=[notification]
    )
    email_sender = MagicMock()
    email_sender.send.return_value = None

    handle_process_notifications(
        cmd, notification_repo, email_sender, post_repo, comment_repo, user_repo
    )

    notification_repo.mark_failed.assert_not_called()


def test_calls_mark_failed_when_max_retries_exhausted() -> None:
    """mark_failed is called on the aggregate and repo.save persists it."""
    notification = _make_notification(notification_id=9, attempt_count=3)
    cmd = _make_command(max_retries=3)
    notification_repo, post_repo, comment_repo, user_repo = _make_repos(
        notifications=[notification]
    )
    email_sender = MagicMock()
    email_sender.send.return_value = None

    handle_process_notifications(
        cmd, notification_repo, email_sender, post_repo, comment_repo, user_repo
    )

    notification.mark_failed.assert_called_once()
    notification_repo.save.assert_called_once_with(notification)


def test_does_not_call_mark_for_retry_when_max_retries_exhausted() -> None:
    """mark_for_retry is not called when attempt_count >= max_retries."""
    notification = _make_notification(attempt_count=3)
    cmd = _make_command(max_retries=3)
    notification_repo, post_repo, comment_repo, user_repo = _make_repos(
        notifications=[notification]
    )
    email_sender = MagicMock()
    email_sender.send.return_value = None

    handle_process_notifications(
        cmd, notification_repo, email_sender, post_repo, comment_repo, user_repo
    )

    notification_repo.mark_for_retry.assert_not_called()


def test_increments_failed_count_when_send_fails() -> None:
    """failed count increments for each notification that cannot be sent."""
    notifications = [
        _make_notification(notification_id=1, attempt_count=3),
        _make_notification(notification_id=2, attempt_count=3),
    ]
    cmd = _make_command(max_retries=3)
    notification_repo, post_repo, comment_repo, user_repo = _make_repos(
        notifications=notifications
    )
    email_sender = MagicMock()
    email_sender.send.return_value = None

    result = handle_process_notifications(
        cmd, notification_repo, email_sender, post_repo, comment_repo, user_repo
    )

    assert result["failed"] == 2


def test_returns_correct_total_in_summary() -> None:
    """total equals sent + failed."""
    notifications = [
        _make_notification(notification_id=1, attempt_count=0),
        _make_notification(notification_id=2, attempt_count=3),
    ]
    cmd = _make_command(max_retries=3)
    notification_repo, post_repo, comment_repo, user_repo = _make_repos(
        notifications=notifications
    )
    email_sender = MagicMock()
    email_sender.send.side_effect = ["resend-ok", None]

    result = handle_process_notifications(
        cmd, notification_repo, email_sender, post_repo, comment_repo, user_repo
    )

    assert result["sent"] == 1
    assert result["failed"] == 1
    assert result["total"] == 2


def test_continues_processing_after_per_notification_exception() -> None:
    """Exception for one notification does not stop processing of others."""
    notifications = [
        _make_notification(notification_id=1),
        _make_notification(notification_id=2),
    ]
    cmd = _make_command()
    notification_repo, post_repo, comment_repo, user_repo = _make_repos(
        notifications=notifications
    )
    email_sender = MagicMock()
    email_sender.send.side_effect = [RuntimeError("transient failure"), "ok-id"]

    result = handle_process_notifications(
        cmd, notification_repo, email_sender, post_repo, comment_repo, user_repo
    )

    assert result["sent"] == 1


def test_never_raises_on_per_notification_exception() -> None:
    """handle_process_notifications does not propagate per-item exceptions."""
    notification = _make_notification()
    cmd = _make_command()
    notification_repo, post_repo, comment_repo, user_repo = _make_repos(
        notifications=[notification]
    )
    email_sender = MagicMock()
    email_sender.send.side_effect = RuntimeError("crash")

    result = handle_process_notifications(
        cmd, notification_repo, email_sender, post_repo, comment_repo, user_repo
    )

    assert isinstance(result, dict)


def test_reply_received_variables_include_required_keys() -> None:
    """Variables dict for reply_received includes all required template keys."""
    notification = _make_notification(event_type="reply_received")
    cmd = _make_command()
    notification_repo, post_repo, comment_repo, user_repo = _make_repos(
        notifications=[notification]
    )
    email_sender = MagicMock()
    email_sender.send.return_value = "ok"

    handle_process_notifications(
        cmd, notification_repo, email_sender, post_repo, comment_repo, user_repo
    )

    call_args = email_sender.send.call_args
    variables: dict = call_args[0][2]
    assert "REPLY_AUTHOR" in variables
    assert "POST_TITLE" in variables
    assert "REPLY_EXCERPT" in variables
    assert "UNSUBSCRIBE_URL" in variables


def test_comment_posted_variables_include_required_keys() -> None:
    """Variables dict for comment_posted includes all required template keys."""
    notification = _make_notification(event_type="comment_posted")
    cmd = _make_command()
    notification_repo, post_repo, comment_repo, user_repo = _make_repos(
        notifications=[notification]
    )
    email_sender = MagicMock()
    email_sender.send.return_value = "ok"

    handle_process_notifications(
        cmd, notification_repo, email_sender, post_repo, comment_repo, user_repo
    )

    call_args = email_sender.send.call_args
    variables: dict = call_args[0][2]
    assert "REPLY_AUTHOR" in variables
    assert "POST_TITLE" in variables
    assert "ORIGINAL_COMMENT" in variables
    assert "UNSUBSCRIBE_URL" in variables


def test_mark_for_retry_receives_future_datetime() -> None:
    """mark_for_retry is called with a next_retry_at in the future."""
    notification = _make_notification(attempt_count=0)
    cmd = _make_command(max_retries=3)
    notification_repo, post_repo, comment_repo, user_repo = _make_repos(
        notifications=[notification]
    )
    email_sender = MagicMock()
    email_sender.send.return_value = None
    before = datetime.now(UTC)

    handle_process_notifications(
        cmd, notification_repo, email_sender, post_repo, comment_repo, user_repo
    )

    call_args = notification_repo.mark_for_retry.call_args
    next_retry_at = call_args[0][1]
    assert next_retry_at > before


def test_notification_with_no_id_increments_failed() -> None:
    """A notification with id=None is counted as failed."""
    notification = _make_notification()
    notification.id = None
    cmd = _make_command()
    notification_repo, post_repo, comment_repo, user_repo = _make_repos(
        notifications=[notification]
    )
    email_sender = MagicMock()

    result = handle_process_notifications(
        cmd, notification_repo, email_sender, post_repo, comment_repo, user_repo
    )

    assert result["failed"] == 1
    assert result["sent"] == 0
    email_sender.send.assert_not_called()


def test_missing_context_marks_notification_failed_in_db() -> None:
    """Notification with missing referenced entity is marked failed."""
    notification = _make_notification(notification_id=42)
    cmd = _make_command()
    notification_repo, post_repo, comment_repo, user_repo = _make_repos(
        notifications=[notification]
    )
    user_repo.find_by_id.return_value = None
    email_sender = MagicMock()

    handle_process_notifications(
        cmd, notification_repo, email_sender, post_repo, comment_repo, user_repo
    )

    notification.mark_failed.assert_called_once()
    notification_repo.save.assert_called_once_with(notification)
    email_sender.send.assert_not_called()


def test_missing_context_increments_failed_count() -> None:
    """Notification skipped for missing context is counted as failed."""
    notification = _make_notification(notification_id=7)
    cmd = _make_command()
    notification_repo, post_repo, comment_repo, user_repo = _make_repos(
        notifications=[notification]
    )
    post_repo.find_by_id.return_value = None
    email_sender = MagicMock()

    result = handle_process_notifications(
        cmd, notification_repo, email_sender, post_repo, comment_repo, user_repo
    )

    assert result["failed"] == 1
    assert result["sent"] == 0


def test_exception_in_loop_increments_failed() -> None:
    """Unhandled per-notification exception is counted as failed."""
    notification = _make_notification(notification_id=1)
    cmd = _make_command()
    notification_repo, post_repo, comment_repo, user_repo = _make_repos(
        notifications=[notification]
    )
    email_sender = MagicMock()
    email_sender.send.side_effect = RuntimeError("crash")

    result = handle_process_notifications(
        cmd, notification_repo, email_sender, post_repo, comment_repo, user_repo
    )

    assert result["failed"] == 1
    assert result["sent"] == 0
