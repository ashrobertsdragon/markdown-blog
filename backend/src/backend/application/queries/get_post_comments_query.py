"""GetPostCommentsQuery and GetPostCommentsResponse for comment listing."""

from dataclasses import dataclass

from backend.domain.aggregates.comment import Comment


@dataclass(frozen=True)
class GetPostCommentsQuery:
    """Query to list comments for a post with pagination.

    Immutable query encapsulating the intent to retrieve a paginated list
    of comments for a specific post. When show_pending is True (admin view),
    deleted and pending-moderation comments are included.

    Attributes:
        post_id: Positive integer referencing the target Post.
        skip: Number of comments to skip for offset pagination (default 0).
        limit: Maximum number of comments to return, 1–100 (default 50).
        show_pending: When True, includes pending/deleted comments (admin).
    """

    post_id: int
    skip: int = 0
    limit: int = 50
    show_pending: bool = False

    def __post_init__(self) -> None:
        """Validate query parameters.

        Raises:
            ValueError: If post_id is not greater than zero.
            ValueError: If skip is negative.
            ValueError: If limit is not between 1 and 100.
        """
        if self.post_id <= 0:
            raise ValueError("post_id must be greater than 0")

        if self.skip < 0:
            raise ValueError("skip must be 0 or greater")

        if not 1 <= self.limit <= 100:
            raise ValueError("limit must be between 1 and 100")


@dataclass
class GetPostCommentsResponse:
    """Response containing a paginated list of comments with metadata.

    Attributes:
        comments: Comment aggregates matching the query for this page.
        total_count: Lower-bound total of comments available from skip
            through the returned page; exact when has_more is False.
        has_more: True when additional comments exist beyond this page.
    """

    comments: list[Comment]
    total_count: int
    has_more: bool
