"""GetCommentQuery for single comment lookup."""

from dataclasses import dataclass


@dataclass(frozen=True)
class GetCommentQuery:
    """Query to retrieve a single comment by its primary key.

    Used for reply thread context, moderation detail views, and
    parent comment existence checks.

    Attributes:
        comment_id: Positive integer primary key of the target Comment.
    """

    comment_id: int

    def __post_init__(self) -> None:
        """Validate query parameters.

        Raises:
            ValueError: If comment_id is not greater than zero.
        """
        if self.comment_id <= 0:
            raise ValueError("comment_id must be greater than 0")
