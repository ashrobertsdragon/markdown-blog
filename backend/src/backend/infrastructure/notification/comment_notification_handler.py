"""Infrastructure handler for queuing comment-related notifications."""

import logging
from datetime import UTC, datetime

from sqlmodel import Session, select

from backend.domain.events.comment_posted import CommentPostedEvent
from backend.domain.events.mention_event import MentionEvent
from backend.domain.events.reply_received import ReplyReceivedEvent
from backend.infrastructure.persistence.database import get_engine
from backend.infrastructure.persistence.models import (
    NotificationModel,
    UserNotificationPreferencesModel,
)

logger = logging.getLogger(__name__)

_EVENT_COMMENT_POSTED = "comment_posted"
_EVENT_MENTION = "mention"
_EVENT_REPLY_RECEIVED = "reply_received"
_STATUS_PENDING = "pending"


def _pref_allowed(session: Session, recipient_id: int, event_type: str) -> bool:
    """Return True if the recipient has not opted out of this event type.

    Defaults to True when no preference row exists (opt-out model).

    Args:
        session: Active SQLModel session.
        recipient_id: User ID of the notification recipient.
        event_type: Discriminator string — 'comment_posted',
            'reply_received', or 'mention'.

    Returns:
        False only when a preference row explicitly disables the
        corresponding notification type.
    """
    prefs = session.exec(
        select(UserNotificationPreferencesModel).where(
            UserNotificationPreferencesModel.user_id == recipient_id
        )
    ).first()

    if prefs is None:
        return True

    match event_type:
        case _ if event_type == _EVENT_MENTION:
            return prefs.notify_on_mentions
        case _:
            return prefs.notify_on_comment_replies


class CommentNotificationHandler:
    """Persists notification records when comment domain events fire.

    Writes a NotificationModel row to the notifications table for each
    event, leaving status='pending' so a background worker can deliver
    the notification asynchronously via email. Skips queuing when the
    recipient has opted out of the relevant notification type.

    Attributes:
        _session: Optional injected SQLModel Session for testing. When
            None the handler opens its own session via Session(get_engine()).
    """

    def __init__(self, session: Session | None = None) -> None:
        """Initialise the handler with an optional session.

        Args:
            session: SQLModel Session for dependency injection in tests.
                     When None, a new Session(get_engine()) is used per call.
        """
        self._session = session

    def queue_comment_posted(self, event: CommentPostedEvent) -> None:
        """Insert a pending notification for a CommentPostedEvent.

        Args:
            event: The domain event carrying comment_id, post_id,
                sender_id, and recipient_id.
        """
        self._queue(
            event_type=_EVENT_COMMENT_POSTED,
            recipient_id=event.recipient_id,
            sender_id=event.sender_id,
            post_id=event.post_id,
            comment_id=event.comment_id,
        )

    def queue_reply_received(self, event: ReplyReceivedEvent) -> None:
        """Insert a pending notification for a ReplyReceivedEvent.

        Args:
            event: The domain event carrying comment_id, post_id,
                sender_id, and recipient_id.
        """
        self._queue(
            event_type=_EVENT_REPLY_RECEIVED,
            recipient_id=event.recipient_id,
            sender_id=event.sender_id,
            post_id=event.post_id,
            comment_id=event.comment_id,
        )

    def queue_mention(self, event: MentionEvent) -> None:
        """Insert a pending notification for a MentionEvent.

        Args:
            event: The domain event carrying comment_id, post_id,
                sender_id, and recipient_id of the mentioned user.
        """
        self._queue(
            event_type=_EVENT_MENTION,
            recipient_id=event.recipient_id,
            sender_id=event.sender_id,
            post_id=event.post_id,
            comment_id=event.comment_id,
        )

    def _queue(
        self,
        event_type: str,
        recipient_id: int,
        sender_id: int,
        post_id: int,
        comment_id: int,
    ) -> None:
        """Queue a notification record if the recipient allows this event.

        Checks the recipient's notification preferences before inserting.
        When the recipient has opted out of the relevant notification type,
        the record is silently dropped rather than queued.

        Args:
            event_type: Discriminator string — 'comment_posted',
                'reply_received', or 'mention'.
            recipient_id: User ID of the notification recipient.
            sender_id: User ID who triggered the event.
            post_id: Post ID associated with the event.
            comment_id: Comment ID that triggered the event.
        """
        model = NotificationModel(
            recipient_id=recipient_id,
            sender_id=sender_id,
            event_type=event_type,
            post_id=post_id,
            comment_id=comment_id,
            status=_STATUS_PENDING,
            attempt_count=0,
            created_at=datetime.now(UTC),
            sent_at=None,
            error_message=None,
        )

        if self._session is not None:
            if not _pref_allowed(self._session, recipient_id, event_type):
                logger.debug(
                    "Skipping %s notification for user %d: opted out",
                    event_type,
                    recipient_id,
                )
                return
            self._session.add(model)
            self._session.commit()
            return

        with Session(get_engine()) as session:
            if not _pref_allowed(session, recipient_id, event_type):
                logger.debug(
                    "Skipping %s notification for user %d: opted out",
                    event_type,
                    recipient_id,
                )
                return
            session.add(model)
            session.commit()
