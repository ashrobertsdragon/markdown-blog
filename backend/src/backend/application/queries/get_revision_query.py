"""GetRevisionQuery and handler for retrieving single revision with content.

This module defines the query object, response object, and handler function
for retrieving a single revision with rendered HTML content. Part of the
Revision Tracking bounded context application layer.
"""

import logging
from dataclasses import dataclass
from uuid import UUID

from backend.domain.aggregates.post_revision import PostRevision
from backend.domain.protocols.services import HtmlSanitizer, MarkdownService
from backend.infrastructure.persistence.post_revision_repository import (
    PostRevisionRepository,
)

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class GetRevisionQuery:
    """Query to retrieve a single revision by commit SHA.

    Immutable query encapsulating the intent to retrieve a specific revision
    identified by its Git commit SHA.

    Attributes:
        post_id: UUID of the post
        commit_sha: Git commit SHA to retrieve
    """

    post_id: UUID
    commit_sha: str

    def __post_init__(self) -> None:
        """Validate query parameters.

        Ensures all parameters are within valid ranges to prevent invalid
        database queries and resource exhaustion.

        Raises:
            ValueError: If commit_sha exceeds 100 characters
        """
        if len(self.commit_sha) > 100:
            raise ValueError(
                f"commit_sha length {len(self.commit_sha)} exceeds maximum "
                f"of 100 characters"
            )


@dataclass(frozen=True)
class GetRevisionResponse:
    """Response containing revision with rendered content.

    Immutable response providing the requested revision along with both
    markdown and rendered HTML content.

    Attributes:
        revision: PostRevision aggregate
        markdown_content: Original markdown content
        html_content: Rendered and sanitized HTML content
    """

    revision: PostRevision
    markdown_content: str
    html_content: str


def get_revision_handler(
    query: GetRevisionQuery,
    revision_repo: PostRevisionRepository,
    markdown_service: MarkdownService,
    html_sanitizer: HtmlSanitizer,
) -> GetRevisionResponse:
    """Handle GetRevisionQuery to retrieve revision with rendered content.

    Orchestrates workflow:
    1. Load revision by SHA
    2. Render markdown to HTML
    3. Sanitize HTML
    4. Return response with revision and content

    Args:
        query: GetRevisionQuery with post_id and commit_sha
        revision_repo: PostRevisionRepository for database access
        markdown_service: Service for rendering markdown to HTML
        html_sanitizer: Service for sanitizing HTML output

    Returns:
        GetRevisionResponse with revision and rendered content

    Raises:
        ValueError: If revision not found
    """
    sha_short = query.commit_sha[:7]
    logger.info(f"Fetching revision {sha_short} for post {query.post_id}")

    revision = revision_repo.find_by_sha(commit_sha=query.commit_sha)

    if revision is None:
        logger.error(f"Revision not found: {sha_short}")
        raise ValueError(
            f"Revision with SHA '{query.commit_sha}' not found for post "
            f"{query.post_id}"
        )

    logger.debug(f"Rendering markdown for revision {sha_short}")
    markdown_content = revision.markdown_content
    html_rendered = markdown_service.render(markdown_content)
    html_content = html_sanitizer.sanitize(html_rendered)

    logger.debug(
        f"Successfully rendered revision {sha_short} "
        f"({len(markdown_content)} chars markdown -> "
        f"{len(html_content)} chars HTML)"
    )

    return GetRevisionResponse(
        revision=revision,
        markdown_content=markdown_content,
        html_content=html_content,
    )
