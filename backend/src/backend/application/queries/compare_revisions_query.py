"""CompareRevisionsQuery and handler for comparing two revisions.

This module defines the query object, response object, and handler function
for comparing two revisions and generating a diff. Part of the Revision
Tracking bounded context application layer.
"""

import logging
from dataclasses import dataclass

from backend.domain.aggregates.post_revision import PostRevision
from backend.domain.protocols.services import DiffService
from backend.infrastructure.persistence.post_revision_repository import (
    PostRevisionRepository,
)

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class CompareRevisionsQuery:
    """Query to compare two revisions and generate a diff.

    Immutable query encapsulating the intent to compare two specific
    revisions identified by their Git commit SHAs.

    Attributes:
        post_id: int ID of the post
        from_sha: Git commit SHA of the source revision
        to_sha: Git commit SHA of the target revision
    """

    post_id: int
    from_sha: str
    to_sha: str

    def __post_init__(self) -> None:
        """Validate query parameters.

        Ensures all parameters are within valid ranges to prevent invalid
        database queries and resource exhaustion.

        Raises:
            ValueError: If from_sha exceeds 100 characters
            ValueError: If to_sha exceeds 100 characters
        """
        if len(self.from_sha) > 100:
            raise ValueError(
                f"from_sha length {len(self.from_sha)} exceeds maximum "
                f"of 100 characters"
            )

        if len(self.to_sha) > 100:
            raise ValueError(
                f"to_sha length {len(self.to_sha)} exceeds maximum "
                f"of 100 characters"
            )


@dataclass(frozen=True)
class CompareRevisionsResponse:
    """Response containing two revisions and their diff.

    Immutable response providing the source and target revisions along
    with a line-by-line diff of their markdown content.

    Attributes:
        from_revision: Source PostRevision aggregate
        to_revision: Target PostRevision aggregate
        diff_lines: List of diff lines showing changes
    """

    from_revision: PostRevision
    to_revision: PostRevision
    diff_lines: list


def compare_revisions_handler(
    query: CompareRevisionsQuery,
    revision_repo: PostRevisionRepository,
    diff_service: DiffService,
) -> CompareRevisionsResponse:
    """Handle CompareRevisionsQuery to generate diff between revisions.

    Orchestrates workflow:
    1. Load source revision by SHA
    2. Load target revision by SHA
    3. Generate diff using DiffService
    4. Return response with revisions and diff

    Args:
        query: CompareRevisionsQuery with post_id, from_sha, and to_sha
        revision_repo: PostRevisionRepository for database access
        diff_service: DiffService for generating text diffs

    Returns:
        CompareRevisionsResponse with revisions and diff lines

    Raises:
        ValueError: If either revision not found
    """
    from_sha_short = query.from_sha[:7]
    to_sha_short = query.to_sha[:7]
    logger.info(
        f"Comparing revisions for post {query.post_id}: "
        f"{from_sha_short} -> {to_sha_short}"
    )

    logger.debug(f"Loading source revision: {from_sha_short}")
    from_revision = revision_repo.find_by_sha(commit_sha=query.from_sha)
    if from_revision is None:
        logger.error(f"Source revision not found: {from_sha_short}")
        raise ValueError(
            f"Revision with SHA '{query.from_sha}' not found for post "
            f"{query.post_id}"
        )

    logger.debug(f"Loading target revision: {to_sha_short}")
    to_revision = revision_repo.find_by_sha(commit_sha=query.to_sha)
    if to_revision is None:
        logger.error(f"Target revision not found: {to_sha_short}")
        raise ValueError(
            f"Revision with SHA '{query.to_sha}' not found for post "
            f"{query.post_id}"
        )

    logger.debug("Generating diff between revisions")
    diff_result = diff_service.diff_text(
        old_content=from_revision.markdown_content,
        new_content=to_revision.markdown_content,
    )

    logger.info(
        f"Successfully generated diff: {len(diff_result.lines)} diff lines"
    )

    formatted_diff_lines = []
    for line in diff_result.lines:
        line_num = (
            line.line_number_new
            if line.type == "addition"
            else line.line_number_old
        )
        formatted_diff_lines.append(
            {"type": line.type, "content": line.content, "lineNumber": line_num}
        )

    return CompareRevisionsResponse(
        from_revision=from_revision,
        to_revision=to_revision,
        diff_lines=formatted_diff_lines,
    )
