"""Handler for ListPostsQuery."""

import math

from backend.application.queries.list_posts_query import (
    ListPostsQuery,
    ListPostsResponse,
)
from backend.infrastructure.persistence.post_repository import PostRepository


def list_posts_query_handler(
    query: ListPostsQuery, post_repo: PostRepository
) -> ListPostsResponse:
    """Execute list posts query with filtering and pagination.

    Retrieves posts for a specific author with optional publication status
    filtering and pagination support. Calculates pagination metadata and
    returns a structured response.

    Args:
        query: ListPostsQuery containing author_id, filter, page, and limit.
        post_repo: PostRepository instance for database access.

    Returns:
        ListPostsResponse with posts, total_count, total_pages, current_page,
        and limit.
    """
    offset = (query.page - 1) * query.limit

    posts, total_count = post_repo.find_by_author_filtered(
        author_id=query.author_id,
        filter_type=query.filter,
        limit=query.limit,
        offset=offset,
    )

    total_pages = math.ceil(total_count / query.limit) if total_count > 0 else 0

    return ListPostsResponse(
        posts=posts,
        total_count=total_count,
        total_pages=total_pages,
        current_page=query.page,
        limit=query.limit,
    )
