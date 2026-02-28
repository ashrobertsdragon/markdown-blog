"""Handler for GetCommentQuery."""

import logging

from backend.application.queries.get_comment_query import GetCommentQuery
from backend.domain.aggregates.comment import Comment
from backend.infrastructure.persistence.comment_repository import (
    CommentRepository,
)

logger = logging.getLogger(__name__)


def handle_get_comment(
    query: GetCommentQuery,
    comment_repository: CommentRepository,
) -> Comment | None:
    """Handle GetCommentQuery to retrieve a single comment by primary key.

    Used for reply thread context, moderation detail views, and parent
    comment existence checks.

    Args:
        query: GetCommentQuery carrying the comment_id to look up.
        comment_repository: CommentRepository used for the lookup.

    Returns:
        Comment aggregate if found, None otherwise.
    """
    logger.debug("Looking up comment %d", query.comment_id)
    return comment_repository.find_by_id(query.comment_id)
