"""Handler for GetPostCommentsQuery."""

import logging

from backend.application.queries.get_post_comments_query import (
    GetPostCommentsQuery,
    GetPostCommentsResponse,
)
from backend.infrastructure.persistence.comment_repository import (
    CommentRepository,
)

logger = logging.getLogger(__name__)


def handle_get_post_comments(
    query: GetPostCommentsQuery,
    comment_repository: CommentRepository,
) -> GetPostCommentsResponse:
    """Handle GetPostCommentsQuery to list comments for a post.

    Uses limit+1 to determine whether more items follow the current page
    without a separate count query. total_count reflects the number of
    items available up to the current page; it is exact when has_more is
    False and a lower bound when has_more is True.

    Args:
        query: GetPostCommentsQuery carrying post_id, skip, limit, and
            show_pending.
        comment_repository: CommentRepository used for comment retrieval.

    Returns:
        GetPostCommentsResponse with comments, total_count, and has_more.
    """
    logger.debug(
        "Fetching comments for post %d (skip=%d, limit=%d, admin=%s)",
        query.post_id,
        query.skip,
        query.limit,
        query.show_pending,
    )

    fetch_limit = query.limit + 1
    if query.show_pending:
        items = comment_repository.list_by_post_admin(
            query.post_id, skip=query.skip, limit=fetch_limit
        )
    else:
        items = comment_repository.list_by_post(
            query.post_id, skip=query.skip, limit=fetch_limit
        )

    has_more = len(items) > query.limit
    comments = items[: query.limit]
    total_count = query.skip + len(comments) + (1 if has_more else 0)

    logger.debug(
        "Returning %d comments for post %d (has_more=%s)",
        len(comments),
        query.post_id,
        has_more,
    )

    return GetPostCommentsResponse(
        comments=comments,
        total_count=total_count,
        has_more=has_more,
    )
