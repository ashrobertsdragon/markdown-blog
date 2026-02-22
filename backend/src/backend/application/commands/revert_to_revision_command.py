"""RevertToRevisionCommand and handler for reverting posts.

This module defines the command object and handler function for reverting
a post to a previous revision via Git SHA. Part of the Revision Tracking
bounded context application layer.
"""

import logging
from dataclasses import dataclass

from backend.domain.aggregates.post_revision import PostRevision
from backend.infrastructure.persistence.filesystem_draft_repository import (
    DraftFile,
    FileSystemDraftRepository,
)
from backend.infrastructure.persistence.post_repository import PostRepository
from backend.infrastructure.persistence.post_revision_repository import (
    PostRevisionRepository,
)
from backend.infrastructure.versioning.github_sync_service import (
    GitHubSyncService,
)
from backend.infrastructure.versioning.mock_github_service import (
    MockGitHubSyncService,
)

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class RevertToRevisionCommand:
    """Command to revert a post to a previous revision.

    This command encapsulates the intent to roll back a post's content to
    a previous state identified by its Git commit SHA. Validation is performed
    at both command and handler layers.

    Attributes:
        slug: URL-safe identifier for the post
        target_sha: Git commit SHA to revert to
        author_id: User ID of the user performing the revert
        user_role: Role of the user (for admin authorization)
    """

    slug: str
    target_sha: str
    author_id: int
    user_role: str

    def __post_init__(self) -> None:
        """Validate input size constraints to prevent resource exhaustion.

        Size validation happens at the command layer to prevent DoS attacks
        and resource exhaustion. Domain validation is deferred to the domain
        layer and handler orchestration logic.

        Raises:
            ValueError: If slug exceeds 1000 characters
            ValueError: If target_sha exceeds 100 characters
            ValueError: If slug is empty
            ValueError: If target_sha is empty
            ValueError: If author_id is not positive
            ValueError: If user_role is empty
        """
        if len(self.slug) > 1000:
            raise ValueError(
                f"slug length {len(self.slug)} exceeds maximum "
                f"of 1000 characters"
            )

        if len(self.target_sha) > 100:
            raise ValueError(
                f"target_sha length {len(self.target_sha)} exceeds maximum "
                f"of 100 characters"
            )

        if not self.slug:
            raise ValueError("slug cannot be empty")

        if not self.target_sha:
            raise ValueError("target_sha cannot be empty")

        if self.author_id <= 0:
            raise ValueError("author_id must be a positive integer")

        if not self.user_role:
            raise ValueError("user_role cannot be empty")


def revert_to_revision_handler(
    command: RevertToRevisionCommand,
    post_repo: PostRepository,
    revision_repo: PostRevisionRepository,
    draft_repo: FileSystemDraftRepository,
    github_service: GitHubSyncService | MockGitHubSyncService,
) -> PostRevision:
    """Handle RevertToRevisionCommand to revert post to previous revision.

    Orchestrates workflow:
    1. Load post aggregate for authorization check
    2. Verify authorization (owner or admin)
    3. Load target revision by SHA
    4. Write reverted markdown to filesystem
    5. Commit to GitHub with revert message
    6. Create new PostRevision record with is_revert=True

    Args:
        command: RevertToRevisionCommand with slug, target_sha, author_id,
            and user_role
        post_repo: PostRepository for loading post aggregate
        revision_repo: PostRevisionRepository for loading/saving revisions
        draft_repo: FileSystemDraftRepository for filesystem operations
        github_service: GitHubSyncService for version control

    Returns:
        PostRevision aggregate representing the revert commit

    Raises:
        ValueError: If post not found
        ValueError: If revision not found
        ValueError: If user not authorized (not owner and not admin)
        RuntimeError: If GitHub service fails (propagated)
    """
    target_sha_short = command.target_sha[:7]
    logger.info(
        f"Starting revert for post '{command.slug}' to SHA {target_sha_short}"
    )
    logger.debug(f"User role: {command.user_role}")

    post = post_repo.find_by_slug(command.slug)
    if post is None:
        logger.error(f"Post not found: '{command.slug}'")
        raise ValueError(f"Post with slug '{command.slug}' not found")

    if post.id is None:
        logger.error(f"Post '{command.slug}' has no ID")
        raise ValueError(f"Post '{command.slug}' has no ID")

    post_id = post.id
    author_id = command.author_id

    if post.author_id != author_id and command.user_role != "admin":
        logger.warning(
            f"Unauthorized revert attempt on post '{command.slug}' "
            f"by user (role: {command.user_role})"
        )
        raise ValueError("Not authorized to revert this post")

    logger.debug(f"Loading target revision: {command.target_sha[:7]}")
    revision = revision_repo.find_by_sha(commit_sha=command.target_sha)
    if revision is None:
        logger.error(f"Revision not found: {command.target_sha[:7]}")
        raise ValueError(
            f"Revision with SHA '{command.target_sha}' not found for post "
            f"'{command.slug}'"
        )

    logger.debug(f"Loading draft file for '{command.slug}'")
    draft = draft_repo.find_by_slug(command.slug)
    if draft is None:
        logger.error(f"Draft file not found for '{command.slug}'")
        raise ValueError(f"Draft file for '{command.slug}' not found")

    logger.info(
        f"Updating draft file for '{command.slug}' with reverted content"
    )
    updated_draft = DraftFile(
        slug=draft.slug,
        title=draft.title,
        author=draft.author,
        content=revision.markdown_content,
        published=draft.published,
        created_at=draft.created_at,
        published_at=draft.published_at,
        tags=draft.tags,
    )
    draft_repo.save(updated_draft)

    short_sha = command.target_sha[:7]
    original_message = revision.commit_message
    revert_message = f"Revert to {short_sha}: {original_message}"

    logger.info(f"Committing revert to GitHub: '{command.slug}'")
    new_commit_sha = github_service.commit_file(
        path=f"drafts/{command.slug}.md",
        content=revision.markdown_content,
        message=revert_message,
    )

    if new_commit_sha is None:
        logger.error(f"Failed to commit revert to GitHub for '{command.slug}'")
        raise RuntimeError("Failed to commit revert to GitHub")

    logger.debug(
        f"Creating PostRevision record for revert (new SHA: "
        f"{new_commit_sha[:7]})"
    )
    new_revision = PostRevision.create(
        post_id=post_id,
        commit_sha=new_commit_sha,
        author_id=author_id,
        commit_message=revert_message,
        markdown_content=revision.markdown_content,
        is_revert=True,
    )

    revision_repo.save(
        post_revision=new_revision,
        post_id=post_id,
        author_id=author_id,
    )

    logger.info(
        f"Successfully reverted post '{command.slug}' to {short_sha} "
        f"(new commit: {new_commit_sha[:7]})"
    )
    return new_revision
