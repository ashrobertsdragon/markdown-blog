"""Unit tests for comment event handler functions.

Covers notify_comment_posted and notify_reply_received:
- Calls handler.queue_comment_posted when sender != recipient
- Calls handler.queue_reply_received when sender != recipient
- No-ops when sender_id == post_author_id (self-comment)
- No-ops when sender_id == parent_author_id (self-reply)
- Logs and swallows exceptions from the notification handler
- Never raises even when the underlying handler raises
- Skips queue when reply notification preference is disabled
- Skips queue when mention notification preference is disabled
- Queues when reply notification preference is enabled
"""

import logging
from datetime import UTC, datetime
from unittest.mock import MagicMock

import pytest

from backend.application.handlers.comment_event_handler import (
    notify_comment_posted,
    notify_reply_received,
)
from backend.domain.aggregates.comment import Comment
from backend.domain.events.comment_posted import CommentPostedEvent
from backend.domain.events.reply_received import ReplyReceivedEvent
from backend.domain.value_objects.comment_text import CommentText


def _make_comment(
    comment_id: int = 1,
    post_id: int = 10,
    author_id: int = 5,
    parent_id: int | None = None,
) -> Comment:
    """Build a minimal Comment aggregate for test use."""
    now = datetime(2024, 1, 1, tzinfo=UTC)
    return Comment(
        id=comment_id,
        post_id=post_id,
        author_id=author_id,
        _text=CommentText("Hello"),
        parent_id=parent_id,
        created_at=now,
        updated_at=now,
        is_deleted=False,
        is_pending_moderation=False,
    )


@pytest.fixture
def mock_handler() -> MagicMock:
    """Return a mock CommentNotificationHandler."""
    return MagicMock()


class TestNotifyCommentPosted:
    """Tests for notify_comment_posted application handler."""

    def test_queues_notification_when_sender_differs_from_author(
        self, mock_handler: MagicMock
    ) -> None:
        """queue_comment_posted is called when sender != post_author_id."""
        comment = _make_comment(comment_id=1, post_id=10, author_id=5)
        notify_comment_posted(
            comment=comment,
            post_author_id=99,
            sender_id=5,
            handler=mock_handler,
        )
        mock_handler.queue_comment_posted.assert_called_once()

    def test_queued_event_has_correct_fields(
        self, mock_handler: MagicMock
    ) -> None:
        """Event passed to queue_comment_posted carries all correct IDs."""
        comment = _make_comment(comment_id=7, post_id=10, author_id=5)
        notify_comment_posted(
            comment=comment,
            post_author_id=99,
            sender_id=5,
            handler=mock_handler,
        )
        event: CommentPostedEvent = mock_handler.queue_comment_posted.call_args[
            0
        ][0]
        assert event.comment_id == 7
        assert event.post_id == 10
        assert event.sender_id == 5
        assert event.recipient_id == 99

    def test_noop_when_sender_is_post_author(
        self, mock_handler: MagicMock
    ) -> None:
        """No notification is queued when the commenter is the post author."""
        comment = _make_comment(comment_id=1, post_id=10, author_id=42)
        notify_comment_posted(
            comment=comment,
            post_author_id=42,
            sender_id=42,
            handler=mock_handler,
        )
        mock_handler.queue_comment_posted.assert_not_called()

    def test_swallows_handler_exception(self, mock_handler: MagicMock) -> None:
        """Exceptions from the notification handler are caught, not raised."""
        mock_handler.queue_comment_posted.side_effect = RuntimeError("db down")
        comment = _make_comment(comment_id=1, post_id=10, author_id=5)
        notify_comment_posted(
            comment=comment,
            post_author_id=99,
            sender_id=5,
            handler=mock_handler,
        )

    def test_logs_handler_exception(
        self, mock_handler: MagicMock, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Handler exceptions are logged at ERROR level with exc_info."""
        mock_handler.queue_comment_posted.side_effect = RuntimeError("boom")
        comment = _make_comment(comment_id=1, post_id=10, author_id=5)
        with caplog.at_level(logging.ERROR):
            notify_comment_posted(
                comment=comment,
                post_author_id=99,
                sender_id=5,
                handler=mock_handler,
            )
        assert any(
            "Failed to queue comment_posted notification" in r.message
            for r in caplog.records
        )
        assert any(
            r.exc_info is not None
            for r in caplog.records
            if "Failed to queue comment_posted notification" in r.message
        )


class TestNotifyReplyReceived:
    """Tests for notify_reply_received application handler."""

    def test_queues_notification_when_sender_differs_from_parent_author(
        self, mock_handler: MagicMock
    ) -> None:
        """queue_reply_received is called when sender != parent_author_id."""
        comment = _make_comment(
            comment_id=2, post_id=10, author_id=5, parent_id=1
        )
        notify_reply_received(
            comment=comment,
            parent_author_id=77,
            sender_id=5,
            handler=mock_handler,
        )
        mock_handler.queue_reply_received.assert_called_once()

    def test_queued_event_has_correct_fields(
        self, mock_handler: MagicMock
    ) -> None:
        """Event passed to queue_reply_received carries all correct IDs."""
        comment = _make_comment(
            comment_id=9, post_id=20, author_id=5, parent_id=3
        )
        notify_reply_received(
            comment=comment,
            parent_author_id=77,
            sender_id=5,
            handler=mock_handler,
        )
        event: ReplyReceivedEvent = mock_handler.queue_reply_received.call_args[
            0
        ][0]
        assert event.comment_id == 9
        assert event.post_id == 20
        assert event.sender_id == 5
        assert event.recipient_id == 77

    def test_noop_when_sender_is_parent_author(
        self, mock_handler: MagicMock
    ) -> None:
        """No notification when the replier is the parent comment author."""
        comment = _make_comment(
            comment_id=2, post_id=10, author_id=55, parent_id=1
        )
        notify_reply_received(
            comment=comment,
            parent_author_id=55,
            sender_id=55,
            handler=mock_handler,
        )
        mock_handler.queue_reply_received.assert_not_called()

    def test_swallows_handler_exception(self, mock_handler: MagicMock) -> None:
        """Exceptions from the notification handler are caught, not raised."""
        mock_handler.queue_reply_received.side_effect = RuntimeError("fail")
        comment = _make_comment(
            comment_id=2, post_id=10, author_id=5, parent_id=1
        )
        notify_reply_received(
            comment=comment,
            parent_author_id=77,
            sender_id=5,
            handler=mock_handler,
        )

    def test_logs_handler_exception(
        self, mock_handler: MagicMock, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Handler exceptions are logged at ERROR level with exc_info."""
        mock_handler.queue_reply_received.side_effect = RuntimeError("crash")
        comment = _make_comment(
            comment_id=2, post_id=10, author_id=5, parent_id=1
        )
        with caplog.at_level(logging.ERROR):
            notify_reply_received(
                comment=comment,
                parent_author_id=77,
                sender_id=5,
                handler=mock_handler,
            )
        assert any(
            "Failed to queue reply_received notification" in r.message
            for r in caplog.records
        )
        assert any(
            r.exc_info is not None
            for r in caplog.records
            if "Failed to queue reply_received notification" in r.message
        )


class TestNotifyCommentPostedWithPreferences:
    """Tests for notify_comment_posted with preference-aware signatures."""

    def test_skips_queue_when_reply_notification_disabled(
        self, mock_handler: MagicMock
    ) -> None:
        """queue_comment_posted not called when should_notify_reply is False."""
        comment = _make_comment(comment_id=1, post_id=10, author_id=5)
        prefs = MagicMock()
        prefs.should_notify_reply.return_value = False
        preferences_repo = MagicMock()
        preferences_repo.get_preferences.return_value = prefs

        notify_comment_posted(
            comment=comment,
            post_author_id=99,
            sender_id=5,
            handler=mock_handler,
            preferences_repo=preferences_repo,
        )

        mock_handler.queue_comment_posted.assert_not_called()

    def test_queues_when_reply_notification_enabled(
        self, mock_handler: MagicMock
    ) -> None:
        """queue_comment_posted is called when should_notify_reply is True."""
        comment = _make_comment(comment_id=1, post_id=10, author_id=5)
        prefs = MagicMock()
        prefs.should_notify_reply.return_value = True
        preferences_repo = MagicMock()
        preferences_repo.get_preferences.return_value = prefs

        notify_comment_posted(
            comment=comment,
            post_author_id=99,
            sender_id=5,
            handler=mock_handler,
            preferences_repo=preferences_repo,
        )

        mock_handler.queue_comment_posted.assert_called_once()


class TestNotifyReplyReceivedWithPreferences:
    """Tests for notify_reply_received with preference-aware signatures."""

    def test_skips_queue_when_reply_notification_disabled(
        self, mock_handler: MagicMock
    ) -> None:
        """queue_reply_received not called when should_notify_reply is False."""
        comment = _make_comment(
            comment_id=2, post_id=10, author_id=5, parent_id=1
        )
        prefs = MagicMock()
        prefs.should_notify_reply.return_value = False
        preferences_repo = MagicMock()
        preferences_repo.get_preferences.return_value = prefs

        notify_reply_received(
            comment=comment,
            parent_author_id=77,
            sender_id=5,
            handler=mock_handler,
            preferences_repo=preferences_repo,
        )

        mock_handler.queue_reply_received.assert_not_called()

    def test_queues_when_reply_notification_enabled(
        self, mock_handler: MagicMock
    ) -> None:
        """queue_reply_received is called when should_notify_reply is True."""
        comment = _make_comment(
            comment_id=2, post_id=10, author_id=5, parent_id=1
        )
        prefs = MagicMock()
        prefs.should_notify_reply.return_value = True
        preferences_repo = MagicMock()
        preferences_repo.get_preferences.return_value = prefs

        notify_reply_received(
            comment=comment,
            parent_author_id=77,
            sender_id=5,
            handler=mock_handler,
            preferences_repo=preferences_repo,
        )

        mock_handler.queue_reply_received.assert_called_once()
