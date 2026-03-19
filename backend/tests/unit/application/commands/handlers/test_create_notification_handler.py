"""Unit tests for handle_create_notification.

Covers:
- Returns None when preferences disable reply notifications (reply_received)
- Returns None when preferences disable mention notifications (mention)
- Calls notification_repo.save() when preferences allow notification
- Returns persisted Notification on success
- Does not call save() when preference is disabled
- Passes correct fields to repository
"""

from unittest.mock import MagicMock

from backend.application.commands.create_notification_command import (
    CreateNotificationCommand,
)
from backend.application.commands.handlers.create_notification_handler import (
    handle_create_notification,
)
from backend.domain.aggregates.notification import Notification


def _make_command(
    *,
    recipient_id: int = 10,
    sender_id: int = 5,
    post_id: int = 100,
    comment_id: int = 50,
    event_type: str = "reply_received",
) -> CreateNotificationCommand:
    """Build a valid CreateNotificationCommand."""
    return CreateNotificationCommand(
        recipient_id=recipient_id,
        sender_id=sender_id,
        post_id=post_id,
        comment_id=comment_id,
        event_type=event_type,
    )


def _make_prefs(
    *, should_reply: bool = True, should_mention: bool = True
) -> MagicMock:
    """Return a mock NotificationPreferences."""
    prefs = MagicMock()
    prefs.should_notify_reply.return_value = should_reply
    prefs.should_notify_mention.return_value = should_mention
    return prefs


def _make_notification_repo(
    saved_notification: Notification | None = None,
) -> MagicMock:
    """Return a mock notification repository."""
    repo = MagicMock()
    if saved_notification is not None:
        repo.save.return_value = saved_notification
    return repo


def _make_preferences_repo(prefs: MagicMock) -> MagicMock:
    """Return a mock preferences repository returning the given prefs."""
    repo = MagicMock()
    repo.get_preferences.return_value = prefs
    return repo


def test_returns_none_when_reply_notification_disabled() -> None:
    """Returns None without saving when reply preference is False."""
    prefs = _make_prefs(should_reply=False)
    notification_repo = _make_notification_repo()
    preferences_repo = _make_preferences_repo(prefs)
    command = _make_command(event_type="reply_received")

    result = handle_create_notification(
        command, notification_repo, preferences_repo
    )

    assert result is None


def test_does_not_save_when_reply_notification_disabled() -> None:
    """notification_repo.save is not called when reply preference is False."""
    prefs = _make_prefs(should_reply=False)
    notification_repo = _make_notification_repo()
    preferences_repo = _make_preferences_repo(prefs)
    command = _make_command(event_type="reply_received")

    handle_create_notification(command, notification_repo, preferences_repo)

    notification_repo.save.assert_not_called()


def test_returns_none_when_mention_notification_disabled() -> None:
    """Returns None without saving when mention preference is False."""
    prefs = _make_prefs(should_mention=False)
    notification_repo = _make_notification_repo()
    preferences_repo = _make_preferences_repo(prefs)
    command = _make_command(event_type="mention")

    result = handle_create_notification(
        command, notification_repo, preferences_repo
    )

    assert result is None


def test_does_not_save_when_mention_notification_disabled() -> None:
    """notification_repo.save is not called when mention preference is False."""
    prefs = _make_prefs(should_mention=False)
    notification_repo = _make_notification_repo()
    preferences_repo = _make_preferences_repo(prefs)
    command = _make_command(event_type="mention")

    handle_create_notification(command, notification_repo, preferences_repo)

    notification_repo.save.assert_not_called()


def test_calls_save_when_preferences_allow_reply() -> None:
    """notification_repo.save is called when reply preference is True."""
    prefs = _make_prefs(should_reply=True)
    notification_repo = _make_notification_repo()
    preferences_repo = _make_preferences_repo(prefs)
    command = _make_command(event_type="reply_received")

    handle_create_notification(command, notification_repo, preferences_repo)

    notification_repo.save.assert_called_once()


def test_returns_persisted_notification_on_success() -> None:
    """Returns the Notification returned by notification_repo.save."""
    prefs = _make_prefs(should_reply=True)
    saved = MagicMock(spec=Notification)
    notification_repo = _make_notification_repo(saved_notification=saved)
    preferences_repo = _make_preferences_repo(prefs)
    command = _make_command(event_type="reply_received")

    result = handle_create_notification(
        command, notification_repo, preferences_repo
    )

    assert result is saved


def test_passes_correct_fields_to_repository() -> None:
    """Save is called with a Notification carrying all command fields."""
    prefs = _make_prefs(should_reply=True)
    notification_repo = _make_notification_repo()
    preferences_repo = _make_preferences_repo(prefs)
    command = _make_command(
        recipient_id=10,
        sender_id=5,
        post_id=100,
        comment_id=50,
        event_type="reply_received",
    )

    handle_create_notification(command, notification_repo, preferences_repo)

    call_args = notification_repo.save.call_args
    saved_notification = call_args[0][0]
    assert saved_notification.recipient_id == 10
    assert saved_notification.sender_id == 5
    assert saved_notification.post_id == 100
    assert saved_notification.comment_id == 50


def test_fetches_preferences_for_correct_recipient() -> None:
    """preferences_repo.get_preferences is called with the recipient_id."""
    prefs = _make_prefs(should_reply=True)
    notification_repo = _make_notification_repo()
    preferences_repo = _make_preferences_repo(prefs)
    command = _make_command(recipient_id=42, event_type="reply_received")

    handle_create_notification(command, notification_repo, preferences_repo)

    preferences_repo.get_preferences.assert_called_once_with(42)
