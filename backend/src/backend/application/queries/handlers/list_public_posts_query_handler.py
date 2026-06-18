"""Handler for ListPublicPostsQuery."""

import math

from backend.application.queries.list_public_posts_query import (
    ListPublicPostsQuery,
    ListPublicPostsResponse,
)
from backend.infrastructure.persistence.post_repository import PostRepository


def list_public_posts_query_handler(
    query: ListPublicPostsQuery, post_repo: PostRepository
) -> ListPublicPostsResponse:
    """Execute list public posts query with pagination."""
    offset = (query.page - 1) * query.limit

    posts = post_repo.list_published(
        limit=query.limit,
        offset=offset,
    )
    total_count = post_repo.count_published()

    total_pages = math.ceil(total_count / query.limit) if total_count > 0 else 0

    return ListPublicPostsResponse(
        posts=posts,
        total_count=total_count,
        total_pages=total_pages,
        current_page=query.page,
        limit=query.limit,
    )
