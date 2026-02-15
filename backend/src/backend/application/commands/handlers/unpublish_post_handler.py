import logging
from typing import TYPE_CHECKING

from backend.application.commands.unpublish_post_command import (
    UnpublishPostCommand,
)

if TYPE_CHECKING:
    from backend.domain.aggregates.post import Post
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


def unpublish_post_handler(
    command: UnpublishPostCommand,
    draft_repo: "FileSystemDraftRepository",
    post_repo: "PostRepository",
    github_service: "GitHubSyncService",
) -> "Post":
    """Unpublish published post: update database, draft file, and GitHub.

    Orchestrates the unpublishing workflow:
    1. Load Post aggregate from database and verify ownership
    2. Validate post is published
    3. Call post.unpublish() domain method
    4. Persist Post to database (ATOMIC - must succeed)
    5. Update draft front matter in filesystem (BEST EFFORT - log on fail)
    6. Commit updated draft to GitHub (BEST EFFORT - log on fail)

    Args:
        command: UnpublishPostCommand with slug, author_id, and user_role
        draft_repo: FileSystemDraftRepository for draft I/O
        post_repo: PostRepository for Post persistence
        github_service: GitHubSyncService for GitHub commits

    Returns:
        Post: Unpublished Post aggregate with published=False

    Raises:
        ValueError: If post not found, user unauthorized, or already unpublished
    """
    logger.debug(f"Loading Post from database: {command.slug}")
    post = post_repo.find_by_slug(command.slug)
    if post is None:
        raise ValueError(f"Post with slug '{command.slug}' not found")

    if post.author_id != command.author_id and command.user_role != "admin":
        logger.warning(
            f"User {command.author_id} attempted to unpublish post "
            f"'{command.slug}' owned by user {post.author_id}"
        )
        raise ValueError("Cannot unpublish another author's post")

    if not post.published:
        raise ValueError(
            f"Post '{command.slug}' is not published (already unpublished)"
        )

    logger.info(f"Unpublishing post: {command.slug}")
    post.unpublish()

    logger.debug(f"Saving unpublished post to database: {command.slug}")
    try:
        post = post_repo.save(post)
        logger.info(f"Post '{command.slug}' unpublished in database")
    except Exception as e:
        logger.error(f"Failed to save post to database: {command.slug}: {e}")
        raise

    logger.debug(f"Loading draft file: {command.slug}")
    draft = draft_repo.find_by_slug(command.slug)

    if draft is None:
        logger.warning(
            f"Draft file not found for '{command.slug}' - "
            "post is unpublished in database, skipping file update"
        )
    else:
        try:
            logger.debug(f"Updating draft front matter: {command.slug}")
            draft.published = False
            draft_repo.save(draft)
            logger.debug(f"Updated draft front matter for {command.slug}")
        except OSError as e:
            logger.warning(
                f"Failed to update draft file for '{command.slug}': {e} - "
                "post is unpublished, draft file state may be stale"
            )

        try:
            logger.debug(f"Committing to GitHub: drafts/{post.slug}.md")
            commit_message = f"Unpublish post: {draft.title}"
            commit_sha = github_service.commit_file(
                path=f"drafts/{post.slug}.md",
                content=draft.to_markdown(),
                message=commit_message,
            )
            if commit_sha is None:
                logger.warning(
                    f"Failed to commit to GitHub for '{command.slug}' - "
                    "post is unpublished, GitHub out of sync"
                )
            else:
                logger.debug(f"Committed to GitHub with SHA: {commit_sha}")
        except Exception as e:
            logger.warning(
                f"GitHub commit exception for '{command.slug}': {e} - "
                "continuing"
            )

    return post
