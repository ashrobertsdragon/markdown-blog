"""ListPublicPostsQuery and ListPublicPostsResponse for public post listing operations."""

from dataclasses import dataclass

from backend.domain.aggregates.post import Post


@dataclass(frozen=True)
class ListPublicPostsQuery:
    """Query to list published posts with pagination."""
    page: int = 1
    limit: int = 20

    def __post_init__(self) -> None:
        """Validate query parameters."""
        if self.page < 1:
            raise ValueError("page must be 1 or greater")
        if not 1 <= self.limit <= 100:
            raise ValueError("limit must be between 1 and 100")


@dataclass(frozen=True)
class ListPublicPostsResponse:
    """Response containing paginated list of public posts with metadata."""
    posts: list[Post]
    total_count: int
    total_pages: int
    current_page: int
    limit: int
