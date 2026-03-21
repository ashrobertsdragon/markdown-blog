"""CreateNotificationCommand for notification creation.

This module defines the command object for creating a new notification record.
Part of the Notification bounded context application layer.
"""

from dataclasses import dataclass

_VALID_EVENT_TYPES = frozenset({"comment_posted", "reply_received", "mention"})


@dataclass(frozen=True)
class CreateNotificationCommand:
    """Command to create a new notification for a user.

    Validates primitive constraints at the command boundary. Domain validation
    is enforced by the Notification aggregate.

    Attributes:
        recipient_id: Positive integer referencing the User to notify.
        sender_id: Positive integer referencing the User who triggered the
            event.
        event_type: Domain event that triggered the notification; must be one of
            'comment_posted', 'reply_received', or 'mention'.
        post_id: Positive integer referencing the related Post.
        comment_id: Positive integer referencing the triggering Comment.
    """

    recipient_id: int
    sender_id: int
    event_type: str
    post_id: int
    comment_id: int

    def __post_init__(self) -> None:
        """Validate primitive constraints before the command is dispatched.

        Raises:
            ValueError: If recipient_id is not greater than zero.
            ValueError: If sender_id is not greater than zero.
            ValueError: If post_id is not greater than zero.
            ValueError: If comment_id is not greater than zero.
            ValueError: If event_type is empty, whitespace-only, or not a
                recognised event type.
        """
        if self.recipient_id <= 0:
            raise ValueError("recipient_id must be greater than 0")

        if self.sender_id <= 0:
            raise ValueError("sender_id must be greater than 0")

        if self.post_id <= 0:
            raise ValueError("post_id must be greater than 0")

        if self.comment_id <= 0:
            raise ValueError("comment_id must be greater than 0")

        stripped = self.event_type.strip()
        if not stripped or stripped not in _VALID_EVENT_TYPES:
            raise ValueError(
                f"event_type must be one of {sorted(_VALID_EVENT_TYPES)}"
            )
