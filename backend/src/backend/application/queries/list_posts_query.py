"""ListPostsQuery and ListPostsResponse for post listing operations."""

from dataclasses import dataclass

from backend.domain.aggregates.post import Post
from backend.domain.value_objects.post_filter import PostFilter


@dataclass(frozen=True)
class ListPostsQuery:
    """Query to list posts for an author with filtering and pagination.

    Immutable query encapsulating the intent to retrieve a paginated
    list of posts for a specific author, optionally filtered by publication
    status. Validation ensures all parameters are within acceptable ranges.

    Attributes:
        author_id: User ID of the post author (must be positive).
        filter: Filter type for publication status (defaults to ALL).
        page: Page number for pagination (1-indexed, defaults to 1).
        limit: Number of posts per page (1-100, defaults to 20).
    """

    author_id: int
    filter: PostFilter = PostFilter.ALL
    page: int = 1
    limit: int = 20

    def __post_init__(self) -> None:
        """Validate query parameters.

        Ensures all parameters are within valid ranges to prevent
        invalid database queries and resource exhaustion.

        Raises:
            ValueError: If any parameter is invalid.
        """
        if self.author_id <= 0:
            raise ValueError("author_id must be a positive integer")

        if self.page < 1:
            raise ValueError("page must be 1 or greater")

        if not 1 <= self.limit <= 100:
            raise ValueError("limit must be between 1 and 100")


@dataclass(frozen=True)
class ListPostsResponse:
    """Response containing paginated list of posts with metadata.

    Immutable response providing the requested posts along with
    pagination metadata for client-side navigation.

    Attributes:
        posts: List of Post aggregates matching the query.
        total_count: Total number of posts matching filter (across all pages).
        total_pages: Total number of pages available.
        current_page: The page number that was requested.
        limit: Number of posts per page.
    """

    posts: list[Post]
    total_count: int
    total_pages: int
    current_page: int
    limit: int
