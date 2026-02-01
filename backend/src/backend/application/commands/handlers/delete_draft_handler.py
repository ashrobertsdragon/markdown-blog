import logging
from typing import TYPE_CHECKING

from backend.application.commands.delete_draft_command import DeleteDraftCommand

if TYPE_CHECKING:
    from backend.infrastructure.persistence.filesystem_draft_repository import (
        FileSystemDraftRepository,
    )
    from backend.infrastructure.persistence.post_repository import (
        PostRepository,
    )
    from backend.infrastructure.versioning.github_sync_service import (
        GitHubSyncService,
    )

logger = logging.getLogger(__name__)


def delete_draft_handler(
    command: DeleteDraftCommand,
    draft_repo: "FileSystemDraftRepository",
    post_repo: "PostRepository",
    github_service: "GitHubSyncService",
) -> None:
    """Delete draft post with GitHub sync.

    Workflow:
    1. Check if post exists and is published (block if published)
    2. Delete from filesystem
    3. Commit deletion to GitHub (CRITICAL - must succeed)

    Args:
        command: DeleteDraftCommand with slug
        draft_repo: Repository for filesystem operations
        post_repo: Repository for checking publication status
        github_service: Service for GitHub deletion

    Raises:
        ValueError: If post is published or filesystem deletion fails
        RuntimeError: If GitHub deletion fails (critical)
    """
    # Step 1: Check publication status
    logger.debug(f"Checking publication status: {command.slug}")
    post = post_repo.find_by_slug(command.slug)

    if post is not None and post.published:
        logger.error(
            f"Cannot delete published post '{command.slug}' - unpublish first"
        )
        raise ValueError(
            f"Cannot delete published post '{command.slug}'. "
            "Unpublish the post first via UnpublishPostCommand"
        )

    # Step 2: Delete from filesystem
    logger.info(f"Deleting draft from filesystem: {command.slug}")
    draft_repo.delete(command.slug)
    logger.debug(f"Filesystem deletion completed: {command.slug}")

    # Step 3: Commit to GitHub (CRITICAL)
    logger.debug(f"Committing deletion to GitHub: drafts/{command.slug}.md")
    commit_message = f"Delete draft: {command.slug}"

    try:
        result = github_service.delete_file(
            path=f"drafts/{command.slug}.md",
            message=commit_message,
        )

        if not result:
            logger.error(
                f"GitHub delete_file returned False for '{command.slug}'"
            )
            raise RuntimeError(
                f"GitHub delete failed for '{command.slug}' - "
                "operation returned False"
            )

        logger.info(f"Successfully deleted draft '{command.slug}' from GitHub")

    except RuntimeError:
        raise
    except Exception as e:
        logger.error(f"GitHub exception for '{command.slug}': {e}")
        raise RuntimeError(
            f"GitHub delete failed for '{command.slug}': {e}"
        ) from e
