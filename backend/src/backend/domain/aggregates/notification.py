"""Notification aggregate for the notification bounded context."""

from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum


class NotificationStatus(StrEnum):
    """Status lifecycle for a queued email notification.

    Attributes:
        PENDING: Notification enqueued but not yet attempted.
        SENT: Notification delivered successfully.
        FAILED: All delivery attempts exhausted without success.
    """

    PENDING = "pending"
    SENT = "sent"
    FAILED = "failed"


class EventType(StrEnum):
    """Domain event types that can trigger a notification.

    Attributes:
        COMMENT_POSTED: A new top-level comment was posted on a post.
        REPLY_RECEIVED: A reply was posted to an existing comment.
    """

    COMMENT_POSTED = "comment_posted"
    REPLY_RECEIVED = "reply_received"


@dataclass(frozen=False)
class Notification:
    """Notification aggregate root for the notification bounded context.

    Represents an outbound email notification triggered by a domain event
    (comment posted or reply received). Tracks delivery status, attempt
    count, and error diagnostics to support retry logic.

    Attributes:
        id: Database primary key, None before persistence.
        recipient_id: Foreign key referencing the User who receives the email.
        sender_id: Foreign key referencing the User whose action triggered it.
        event_type: Domain event that triggered the notification.
        post_id: Foreign key referencing the Post the event relates to.
        comment_id: Foreign key referencing the Comment that triggered this.
        status: Current delivery lifecycle state.
        attempt_count: Number of delivery attempts made so far.
        created_at: UTC timestamp set at enqueue time, immutable.
        sent_at: UTC timestamp of successful delivery, None until sent.
        error_message: Last error from a failed attempt, None until failure.
    """

    _MAX_ERROR_LENGTH = 500

    id: int | None
    recipient_id: int
    sender_id: int
    event_type: EventType
    post_id: int
    comment_id: int
    status: NotificationStatus
    attempt_count: int
    created_at: datetime
    sent_at: datetime | None
    error_message: str | None

    def __setattr__(self, name: str, value: object) -> None:
        """Prevent modification of created_at after initialisation.

        Raises:
            AttributeError: If name is 'created_at' and already set.
        """
        if name == "created_at" and hasattr(self, "created_at"):
            raise AttributeError(
                "Cannot modify created_at timestamp - audit trail integrity"
            )
        object.__setattr__(self, name, value)

    @classmethod
    def create(
        cls,
        recipient_id: int,
        sender_id: int,
        event_type: EventType,
        post_id: int,
        comment_id: int,
    ) -> "Notification":
        """Create a new Notification aggregate, ready for persistence.

        Args:
            recipient_id: Positive integer referencing the recipient User.
            sender_id: Positive integer referencing the sender User.
            event_type: Domain event that triggered the notification.
            post_id: Positive integer referencing the related Post.
            comment_id: Positive integer referencing the triggering Comment.

        Returns:
            New Notification with id=None, status=PENDING, attempt_count=0.

        Raises:
            ValueError: If any of recipient_id, sender_id, post_id, or
                comment_id is not a positive integer.
        """
        if recipient_id <= 0:
            raise ValueError("recipient_id must be positive")
        if sender_id <= 0:
            raise ValueError("sender_id must be positive")
        if post_id <= 0:
            raise ValueError("post_id must be positive")
        if comment_id <= 0:
            raise ValueError("comment_id must be positive")

        return cls(
            id=None,
            recipient_id=recipient_id,
            sender_id=sender_id,
            event_type=event_type,
            post_id=post_id,
            comment_id=comment_id,
            status=NotificationStatus.PENDING,
            attempt_count=0,
            created_at=datetime.now(UTC),
            sent_at=None,
            error_message=None,
        )

    def mark_sent(self) -> None:
        """Transition status to SENT and record delivery timestamp.

        Sets status to SENT and populates sent_at with the current UTC time.
        Called by the delivery handler after a successful email send.
        """
        self.status = NotificationStatus.SENT
        self.sent_at = datetime.now(UTC)

    def mark_failed(self, error_message: str) -> None:
        """Transition status to FAILED and record the error.

        Sets status to FAILED and stores the error_message for operator
        diagnostics. Called by the delivery handler after an unrecoverable
        send error.

        Args:
            error_message: Human-readable description of the failure cause.
        """
        self.status = NotificationStatus.FAILED
        self.error_message = error_message[: self._MAX_ERROR_LENGTH]

    def increment_attempt(self) -> None:
        """Increment the delivery attempt counter by one.

        Called by the retry scheduler before each attempt so the maximum
        retry policy can be enforced downstream.
        """
        self.attempt_count += 1

    def to_dict(self) -> dict[str, object]:
        """Serialise the Notification to a JSON-serialisable dictionary.

        Converts enums to their string value and datetimes to ISO 8601
        strings. None fields are preserved as None for explicit serialisation.

        Returns:
            Dictionary containing all Notification fields as primitives.
        """
        return {
            "id": self.id,
            "recipient_id": self.recipient_id,
            "sender_id": self.sender_id,
            "event_type": self.event_type,
            "post_id": self.post_id,
            "comment_id": self.comment_id,
            "status": self.status.value,
            "attempt_count": self.attempt_count,
            "created_at": self.created_at.isoformat(),
            "sent_at": self.sent_at.isoformat() if self.sent_at else None,
            "error_message": self.error_message,
        }
