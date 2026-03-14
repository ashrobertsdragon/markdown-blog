"""Domain event raised when a user posts a new comment on a post."""

from dataclasses import dataclass


@dataclass(frozen=True)
class CommentPostedEvent:
    """Immutable event representing a new top-level comment being posted.

    Attributes:
        comment_id: Primary key of the newly created comment.
        post_id: Primary key of the post the comment belongs to.
        sender_id: User ID of the comment author.
        recipient_id: User ID of the post author who should be notified.
    """

    comment_id: int
    post_id: int
    sender_id: int
    recipient_id: int
