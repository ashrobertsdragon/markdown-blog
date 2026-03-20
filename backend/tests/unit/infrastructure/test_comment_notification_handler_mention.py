"""Unit tests for CommentNotificationHandler.queue_mention().

Covers:
- queue_mention() adds a NotificationModel with event_type="mention"
- NotificationModel fields match the MentionEvent (recipient_id, sender_id,
  post_id, comment_id, status="pending")
- Handler uses the injected session when provided
"""

from unittest.mock import MagicMock

import pytest

from backend.domain.events.mention_event import MentionEvent
from backend.infrastructure.notification.comment_notification_handler import (
    CommentNotificationHandler,
)
from backend.infrastructure.persistence.models import NotificationModel


@pytest.fixture
def mock_session() -> MagicMock:
    """Return a MagicMock standing in for a SQLModel Session."""
    return MagicMock()


@pytest.fixture
def handler(mock_session: MagicMock) -> CommentNotificationHandler:
    """Return a handler wired to the mock session."""
    return CommentNotificationHandler(session=mock_session)


class TestQueueMention:
    """Tests for CommentNotificationHandler.queue_mention()."""

    def test_adds_and_commits_notification(
        self, handler: CommentNotificationHandler, mock_session: MagicMock
    ) -> None:
        """queue_mention adds a model to the session and commits."""
        event = MentionEvent(
            comment_id=1, post_id=2, sender_id=3, recipient_id=4
        )
        handler.queue_mention(event)
        mock_session.add.assert_called_once()
        mock_session.commit.assert_called_once()

    def test_notification_has_mention_event_type(
        self, handler: CommentNotificationHandler, mock_session: MagicMock
    ) -> None:
        """Queued notification carries event_type='mention'."""
        event = MentionEvent(
            comment_id=1, post_id=2, sender_id=3, recipient_id=4
        )
        handler.queue_mention(event)
        model: NotificationModel = mock_session.add.call_args[0][0]
        assert model.event_type == "mention"

    def test_notification_status_is_pending(
        self, handler: CommentNotificationHandler, mock_session: MagicMock
    ) -> None:
        """Queued notification starts with status='pending'."""
        event = MentionEvent(
            comment_id=1, post_id=2, sender_id=3, recipient_id=4
        )
        handler.queue_mention(event)
        model: NotificationModel = mock_session.add.call_args[0][0]
        assert model.status == "pending"

    def test_notification_fields_match_event(
        self, handler: CommentNotificationHandler, mock_session: MagicMock
    ) -> None:
        """recipient_id, sender_id, post_id, comment_id mirror the event."""
        event = MentionEvent(
            comment_id=10, post_id=20, sender_id=30, recipient_id=40
        )
        handler.queue_mention(event)
        model: NotificationModel = mock_session.add.call_args[0][0]
        assert model.recipient_id == 40
        assert model.sender_id == 30
        assert model.post_id == 20
        assert model.comment_id == 10

    def test_uses_injected_session(self, mock_session: MagicMock) -> None:
        """Handler routes through the injected session, not a new one."""
        handler = CommentNotificationHandler(session=mock_session)
        event = MentionEvent(
            comment_id=5, post_id=6, sender_id=7, recipient_id=8
        )
        handler.queue_mention(event)
        mock_session.add.assert_called_once()
        mock_session.commit.assert_called_once()
