"""Domain event raised when a user is mentioned in a comment."""

from dataclasses import dataclass


@dataclass(frozen=True)
class MentionEvent:
    """Immutable event representing a user being @mentioned in a comment.

    Attributes:
        comment_id: Primary key of the comment containing the mention.
        post_id: Primary key of the post the comment belongs to.
        sender_id: User ID of the comment author who wrote the mention.
        recipient_id: User ID of the mentioned user who should be notified.
    """

    comment_id: int
    post_id: int
    sender_id: int
    recipient_id: int
