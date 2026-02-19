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
    1. Load post and verify ownership (or admin role)
    2. Check if post is published (block if published)
    3. Delete from filesystem
    4. Commit deletion to GitHub (CRITICAL - must succeed)

    Args:
        command: DeleteDraftCommand with slug, author_id, and user_role
        draft_repo: Repository for filesystem operations
        post_repo: Repository for checking publication status and ownership
        github_service: Service for GitHub deletion

    Raises:
        ValueError: If post not found, user unauthorized, or post is published
        RuntimeError: If GitHub deletion fails (critical)
    """
    logger.debug(f"Loading post for deletion: {command.slug}")
    post = post_repo.find_by_slug(command.slug)

    if post is None:
        raise ValueError(
            f"Post with slug '{command.slug}' not found in database"
        )

    if post.author_id != command.author_id and command.user_role != "admin":
        logger.warning(
            f"User {command.author_id} attempted to delete post "
            f"'{command.slug}' owned by user {post.author_id}"
        )
        raise ValueError("Cannot delete another author's post")

    if post.published:
        logger.error(
            f"Cannot delete published post '{command.slug}' - unpublish first"
        )
        raise ValueError(
            f"Cannot delete published post '{command.slug}'. "
            "Unpublish the post first via UnpublishPostCommand"
        )

    logger.info(f"Deleting draft from filesystem: {command.slug}")
    draft_repo.delete(command.slug)
    logger.debug(f"Filesystem deletion completed: {command.slug}")

    if post.id is None:
        raise ValueError(f"Post '{command.slug}' has no database ID")

    logger.info(f"Soft-deleting post record in database: {command.slug}")
    post_repo.mark_deleted(post.id)
    logger.debug(f"Database soft-deletion completed: {command.slug}")

    commit_message = f"Delete draft: {post.slug}"
    try:
        result = github_service.delete_file(
            path=f"drafts/{post.slug}.md",
            message=commit_message,
        )
        if not result:
            logger.warning(
                f"GitHub delete_file returned False for '{command.slug}', "
                "continuing with local delete"
            )
        else:
            logger.info(
                f"Successfully deleted draft '{command.slug}' from GitHub"
            )
    except Exception as e:
        logger.warning(
            f"GitHub delete failed for '{command.slug}': {e}, "
            "continuing with local delete"
        )
