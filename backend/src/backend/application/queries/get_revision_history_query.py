"""GetRevisionHistoryQuery and handler for revision history listing.

This module defines the query object, response object, and handler function
for retrieving paginated revision history for a post. Part of the Revision
Tracking bounded context application layer.
"""

import logging
from dataclasses import dataclass

from backend.domain.aggregates.post_revision import PostRevision
from backend.infrastructure.persistence.post_revision_repository import (
    PostRevisionRepository,
)

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class GetRevisionHistoryQuery:
    """Query to retrieve paginated revision history for a post.

    Immutable query encapsulating the intent to retrieve a paginated list
    of revisions for a specific post.

    Attributes:
        post_id: int ID of the post to retrieve revisions for
        skip: Number of records to skip (for pagination, 0-10000)
        limit: Number of records to return (1-100)
    """

    post_id: int
    skip: int
    limit: int

    def __post_init__(self) -> None:
        """Validate query parameters.

        Ensures all parameters are within valid ranges to prevent invalid
        database queries and resource exhaustion.

        Raises:
            ValueError: If skip is outside 0-10000 range
            ValueError: If limit is outside 1-100 range
        """
        if not 0 <= self.skip <= 10000:
            raise ValueError("skip must be between 0 and 10000")

        if not 1 <= self.limit <= 100:
            raise ValueError("limit must be between 1 and 100")


@dataclass(frozen=True)
class GetRevisionHistoryResponse:
    """Response containing paginated revision history.

    Immutable response providing requested revisions along with pagination
    metadata for client-side navigation.

    Attributes:
        revisions: List of PostRevision aggregates
        total_count: Total number of revisions for this post (all pages)
        has_more: Whether there are more revisions beyond this page
    """

    revisions: list[PostRevision]
    total_count: int
    has_more: bool


def get_revision_history_handler(
    query: GetRevisionHistoryQuery,
    revision_repo: PostRevisionRepository,
) -> GetRevisionHistoryResponse:
    """Handle GetRevisionHistoryQuery to retrieve revision history.

    Orchestrates workflow:
    1. Query PostRevisionRepository for paginated revisions
    2. Calculate pagination metadata
    3. Return response with revisions and metadata

    Args:
        query: GetRevisionHistoryQuery with post_id, skip, and limit
        revision_repo: PostRevisionRepository for database access

    Returns:
        GetRevisionHistoryResponse with revisions and pagination metadata
    """
    logger.info(
        f"Fetching revision history for post {query.post_id} "
        f"(skip={query.skip}, limit={query.limit})"
    )

    revisions, total_count = revision_repo.find_by_post_id(
        post_id=query.post_id, skip=query.skip, limit=query.limit
    )

    has_more = (query.skip + query.limit) < total_count

    logger.debug(
        f"Retrieved {len(revisions)} revisions (total: {total_count}, "
        f"has_more: {has_more})"
    )

    return GetRevisionHistoryResponse(
        revisions=revisions, total_count=total_count, has_more=has_more
    )
