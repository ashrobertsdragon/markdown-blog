"""Domain event raised when a user replies to an existing comment."""

from dataclasses import dataclass


@dataclass(frozen=True)
class ReplyReceivedEvent:
    """Immutable event representing a reply to an existing comment.

    Attributes:
        comment_id: Primary key of the newly created reply comment.
        post_id: Primary key of the post the reply belongs to.
        sender_id: User ID of the reply author.
        recipient_id: User ID of the parent comment author to notify.
    """

    comment_id: int
    post_id: int
    sender_id: int
    recipient_id: int
