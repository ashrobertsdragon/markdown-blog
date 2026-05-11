import logging
from typing import TYPE_CHECKING

from backend.application.commands.unpublish_post_command import (
    UnpublishPostCommand,
)
from backend.exceptions import NotFoundError

if TYPE_CHECKING:
    from backend.domain.aggregates.post import Post
    from backend.domain.protocols.services import GitHubSyncService
    from backend.infrastructure.persistence.filesystem_draft_repository import (
        FileSystemDraftRepository,
    )
    from backend.infrastructure.persistence.post_repository import (
        PostRepository,
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
    logger.debug("Loading Post from database: id=%d", command.post_id)
    post = post_repo.find_by_id(command.post_id)
    if post is None:
        raise NotFoundError(f"Post with id {command.post_id} not found")

    slug = post.slug.value

    if post.author_id != command.author_id and command.user_role != "admin":
        logger.warning(
            "User %d attempted to unpublish post '%s' owned by user %d",
            command.author_id,
            slug,
            post.author_id,
        )
        raise ValueError("Cannot unpublish another author's post")

    if not post.published:
        raise ValueError(
            f"Post '{slug}' is not published (already unpublished)"
        )

    logger.info("Unpublishing post: %s", slug)
    post.unpublish()

    logger.debug("Saving unpublished post to database: %s", slug)
    try:
        post = post_repo.save(post)
        logger.info("Post '%s' unpublished in database", slug)
    except Exception as e:
        logger.error("Failed to save post to database: %s: %s", slug, e)
        raise

    logger.debug("Loading draft file: %s", slug)
    draft = draft_repo.find_by_slug(slug)

    if draft is None:
        logger.warning(
            "Draft file not found for '%s' - "
            "post is unpublished in database, skipping file update",
            slug,
        )
    else:
        try:
            logger.debug("Updating draft front matter: %s", slug)
            draft.published = False
            draft_repo.save(draft)
            logger.debug("Updated draft front matter for %s", slug)
        except OSError as e:
            logger.warning(
                "Failed to update draft file for '%s': %s - "
                "post is unpublished, draft file state may be stale",
                slug,
                e,
            )
        else:
            try:
                logger.debug("Committing to GitHub: drafts/%s.md", slug)
                commit_message = f"Unpublish post: {draft.title}"
                commit_sha = github_service.commit_file(
                    path=f"drafts/{slug}.md",
                    content=draft.to_markdown(),
                    message=commit_message,
                )
                if commit_sha is None:
                    logger.warning(
                        "Failed to commit to GitHub for '%s' - "
                        "post is unpublished, GitHub out of sync",
                        slug,
                    )
                else:
                    logger.debug("Committed to GitHub with SHA: %s", commit_sha)
            except Exception as e:
                logger.warning(
                    "GitHub commit exception for '%s': %s - continuing",
                    slug,
                    e,
                )

    return post
