"""Unit tests for CommentNotificationHandler.

Covers:
- queue_comment_posted() inserts a NotificationModel with event_type
  "comment_posted" and status "pending"
- queue_reply_received() inserts a NotificationModel with event_type
  "reply_received" and status "pending"
- Both methods set recipient_id, sender_id, post_id, comment_id from event
- Both methods set attempt_count=0 and sent_at=None
- Both methods set created_at to a UTC datetime
- Handler uses injected session when provided (no real DB required)
"""

from datetime import UTC, datetime
from unittest.mock import MagicMock

import pytest

from backend.domain.events.comment_posted import CommentPostedEvent
from backend.domain.events.reply_received import ReplyReceivedEvent
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


class TestQueueCommentPosted:
    """Tests for CommentNotificationHandler.queue_comment_posted()."""

    def test_adds_and_commits_notification(
        self, handler: CommentNotificationHandler, mock_session: MagicMock
    ) -> None:
        """queue_comment_posted adds a model to the session and commits."""
        event = CommentPostedEvent(
            comment_id=1, post_id=2, sender_id=3, recipient_id=4
        )
        handler.queue_comment_posted(event)
        mock_session.add.assert_called_once()
        mock_session.commit.assert_called_once()

    def test_notification_has_comment_posted_event_type(
        self, handler: CommentNotificationHandler, mock_session: MagicMock
    ) -> None:
        """Queued notification carries event_type='comment_posted'."""
        event = CommentPostedEvent(
            comment_id=1, post_id=2, sender_id=3, recipient_id=4
        )
        handler.queue_comment_posted(event)
        model: NotificationModel = mock_session.add.call_args[0][0]
        assert model.event_type == "comment_posted"

    def test_notification_fields_match_event(
        self, handler: CommentNotificationHandler, mock_session: MagicMock
    ) -> None:
        """recipient_id, sender_id, post_id, comment_id mirror the event."""
        event = CommentPostedEvent(
            comment_id=10, post_id=20, sender_id=30, recipient_id=40
        )
        handler.queue_comment_posted(event)
        model: NotificationModel = mock_session.add.call_args[0][0]
        assert model.recipient_id == 40
        assert model.sender_id == 30
        assert model.post_id == 20
        assert model.comment_id == 10

    def test_notification_initial_state(
        self, handler: CommentNotificationHandler, mock_session: MagicMock
    ) -> None:
        """Queued notification starts with status=pending, attempt_count=0."""
        event = CommentPostedEvent(
            comment_id=1, post_id=2, sender_id=3, recipient_id=4
        )
        handler.queue_comment_posted(event)
        model: NotificationModel = mock_session.add.call_args[0][0]
        assert model.status == "pending"
        assert model.attempt_count == 0
        assert model.sent_at is None

    def test_notification_created_at_is_utc(
        self, handler: CommentNotificationHandler, mock_session: MagicMock
    ) -> None:
        """created_at is a UTC-aware datetime set at queue time."""
        before = datetime.now(UTC)
        event = CommentPostedEvent(
            comment_id=1, post_id=2, sender_id=3, recipient_id=4
        )
        handler.queue_comment_posted(event)
        after = datetime.now(UTC)
        model: NotificationModel = mock_session.add.call_args[0][0]
        assert model.created_at.tzinfo is not None
        assert before <= model.created_at <= after


class TestQueueReplyReceived:
    """Tests for CommentNotificationHandler.queue_reply_received()."""

    def test_adds_and_commits_notification(
        self, handler: CommentNotificationHandler, mock_session: MagicMock
    ) -> None:
        """queue_reply_received adds a model to the session and commits."""
        event = ReplyReceivedEvent(
            comment_id=5, post_id=6, sender_id=7, recipient_id=8
        )
        handler.queue_reply_received(event)
        mock_session.add.assert_called_once()
        mock_session.commit.assert_called_once()

    def test_notification_has_reply_received_event_type(
        self, handler: CommentNotificationHandler, mock_session: MagicMock
    ) -> None:
        """Queued notification carries event_type='reply_received'."""
        event = ReplyReceivedEvent(
            comment_id=5, post_id=6, sender_id=7, recipient_id=8
        )
        handler.queue_reply_received(event)
        model: NotificationModel = mock_session.add.call_args[0][0]
        assert model.event_type == "reply_received"

    def test_notification_fields_match_event(
        self, handler: CommentNotificationHandler, mock_session: MagicMock
    ) -> None:
        """recipient_id, sender_id, post_id, comment_id mirror the event."""
        event = ReplyReceivedEvent(
            comment_id=50, post_id=60, sender_id=70, recipient_id=80
        )
        handler.queue_reply_received(event)
        model: NotificationModel = mock_session.add.call_args[0][0]
        assert model.recipient_id == 80
        assert model.sender_id == 70
        assert model.post_id == 60
        assert model.comment_id == 50

    def test_notification_initial_state(
        self, handler: CommentNotificationHandler, mock_session: MagicMock
    ) -> None:
        """Queued notification starts with status=pending, attempt_count=0."""
        event = ReplyReceivedEvent(
            comment_id=5, post_id=6, sender_id=7, recipient_id=8
        )
        handler.queue_reply_received(event)
        model: NotificationModel = mock_session.add.call_args[0][0]
        assert model.status == "pending"
        assert model.attempt_count == 0
        assert model.sent_at is None

    def test_notification_created_at_is_utc(
        self, handler: CommentNotificationHandler, mock_session: MagicMock
    ) -> None:
        """created_at is a UTC-aware datetime set at queue time."""
        before = datetime.now(UTC)
        event = ReplyReceivedEvent(
            comment_id=5, post_id=6, sender_id=7, recipient_id=8
        )
        handler.queue_reply_received(event)
        after = datetime.now(UTC)
        model: NotificationModel = mock_session.add.call_args[0][0]
        assert model.created_at.tzinfo is not None
        assert before <= model.created_at <= after

    def test_two_queued_notifications_get_two_commits(
        self, handler: CommentNotificationHandler, mock_session: MagicMock
    ) -> None:
        """Each queue call results in a separate commit."""
        e1 = ReplyReceivedEvent(
            comment_id=1, post_id=2, sender_id=3, recipient_id=4
        )
        e2 = ReplyReceivedEvent(
            comment_id=5, post_id=6, sender_id=7, recipient_id=8
        )
        handler.queue_reply_received(e1)
        handler.queue_reply_received(e2)
        assert mock_session.commit.call_count == 2
        assert mock_session.add.call_count == 2


class TestFallbackDbPath:
    """Tests for the no-session (fallback DB) path in _persist().

    Mocks Session and get_engine at the handler module level so that
    Session(get_engine()) is intercepted without touching a real database.
    These tests are written for the refactored implementation that uses
    ``Session(get_engine())`` instead of ``for session in get_db()``.
    """

    def _make_mock_session(self) -> MagicMock:
        """Return a MagicMock that acts as a context-manager session."""
        session = MagicMock()
        session.__enter__ = MagicMock(return_value=session)
        session.__exit__ = MagicMock(return_value=False)
        return session

    def test_queue_comment_posted_uses_fallback_session(self) -> None:
        """queue_comment_posted commits via Session(get_engine())."""
        from unittest.mock import patch

        mock_engine = MagicMock()
        mock_session = self._make_mock_session()

        with (
            patch(
                "backend.infrastructure.notification"
                ".comment_notification_handler.get_engine",
                return_value=mock_engine,
            ),
            patch(
                "backend.infrastructure.notification"
                ".comment_notification_handler.Session",
                return_value=mock_session,
            ) as mock_session_cls,
        ):
            handler = CommentNotificationHandler()
            event = CommentPostedEvent(
                comment_id=1, post_id=2, sender_id=3, recipient_id=4
            )
            handler.queue_comment_posted(event)

            mock_session_cls.assert_called_once_with(mock_engine)
            mock_session.add.assert_called_once()
            mock_session.commit.assert_called_once()

    def test_queue_comment_posted_fallback_notification_fields(self) -> None:
        """Fallback path inserts a NotificationModel with correct fields."""
        from unittest.mock import patch

        mock_engine = MagicMock()
        mock_session = self._make_mock_session()

        with (
            patch(
                "backend.infrastructure.notification"
                ".comment_notification_handler.get_engine",
                return_value=mock_engine,
            ),
            patch(
                "backend.infrastructure.notification"
                ".comment_notification_handler.Session",
                return_value=mock_session,
            ),
        ):
            handler = CommentNotificationHandler()
            event = CommentPostedEvent(
                comment_id=11, post_id=22, sender_id=33, recipient_id=44
            )
            handler.queue_comment_posted(event)

            model: NotificationModel = mock_session.add.call_args[0][0]
            assert model.event_type == "comment_posted"
            assert model.comment_id == 11
            assert model.post_id == 22
            assert model.sender_id == 33
            assert model.recipient_id == 44
            assert model.status == "pending"
            assert model.attempt_count == 0
            assert model.sent_at is None

    def test_queue_reply_received_uses_fallback_session(self) -> None:
        """queue_reply_received commits via Session(get_engine())."""
        from unittest.mock import patch

        mock_engine = MagicMock()
        mock_session = self._make_mock_session()

        with (
            patch(
                "backend.infrastructure.notification"
                ".comment_notification_handler.get_engine",
                return_value=mock_engine,
            ),
            patch(
                "backend.infrastructure.notification"
                ".comment_notification_handler.Session",
                return_value=mock_session,
            ) as mock_session_cls,
        ):
            handler = CommentNotificationHandler()
            event = ReplyReceivedEvent(
                comment_id=5, post_id=6, sender_id=7, recipient_id=8
            )
            handler.queue_reply_received(event)

            mock_session_cls.assert_called_once_with(mock_engine)
            mock_session.add.assert_called_once()
            mock_session.commit.assert_called_once()

    def test_queue_reply_received_fallback_notification_fields(self) -> None:
        """Fallback path inserts NotificationModel with reply_received data."""
        from unittest.mock import patch

        mock_engine = MagicMock()
        mock_session = self._make_mock_session()

        with (
            patch(
                "backend.infrastructure.notification"
                ".comment_notification_handler.get_engine",
                return_value=mock_engine,
            ),
            patch(
                "backend.infrastructure.notification"
                ".comment_notification_handler.Session",
                return_value=mock_session,
            ),
        ):
            handler = CommentNotificationHandler()
            event = ReplyReceivedEvent(
                comment_id=55, post_id=66, sender_id=77, recipient_id=88
            )
            handler.queue_reply_received(event)

            model: NotificationModel = mock_session.add.call_args[0][0]
            assert model.event_type == "reply_received"
            assert model.comment_id == 55
            assert model.post_id == 66
            assert model.sender_id == 77
            assert model.recipient_id == 88
            assert model.status == "pending"
            assert model.attempt_count == 0
            assert model.sent_at is None

    def test_queue_comment_posted_propagates_db_error(self) -> None:
        """DB errors in the fallback path bubble up to the caller."""
        from unittest.mock import patch

        mock_engine = MagicMock()
        mock_session = self._make_mock_session()
        mock_session.commit.side_effect = RuntimeError("DB unavailable")

        with (
            patch(
                "backend.infrastructure.notification.comment_notification_handler.get_engine",
                return_value=mock_engine,
            ),
            patch(
                "backend.infrastructure.notification.comment_notification_handler.Session",
                return_value=mock_session,
            ),
        ):
            handler = CommentNotificationHandler()
            event = CommentPostedEvent(
                comment_id=1, post_id=2, sender_id=3, recipient_id=4
            )
            with pytest.raises(RuntimeError, match="DB unavailable"):
                handler.queue_comment_posted(event)

    def test_queue_reply_received_propagates_db_error(self) -> None:
        """DB errors in the fallback path bubble up to the caller."""
        from unittest.mock import patch

        mock_engine = MagicMock()
        mock_session = self._make_mock_session()
        mock_session.commit.side_effect = RuntimeError("connection refused")

        with (
            patch(
                "backend.infrastructure.notification.comment_notification_handler.get_engine",
                return_value=mock_engine,
            ),
            patch(
                "backend.infrastructure.notification.comment_notification_handler.Session",
                return_value=mock_session,
            ),
        ):
            handler = CommentNotificationHandler()
            event = ReplyReceivedEvent(
                comment_id=5, post_id=6, sender_id=7, recipient_id=8
            )
            with pytest.raises(RuntimeError, match="connection refused"):
                handler.queue_reply_received(event)
