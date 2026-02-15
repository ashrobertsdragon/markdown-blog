import logging
from typing import TYPE_CHECKING

from backend.application.commands.publish_post_command import PublishPostCommand

if TYPE_CHECKING:
    from backend.domain.aggregates.post import Post
    from backend.infrastructure.markdown.markdown_rendering_service import (
        MarkdownRenderingService,
    )
    from backend.infrastructure.persistence.filesystem_draft_repository import (
        FileSystemDraftRepository,
    )
    from backend.infrastructure.persistence.post_repository import (
        PostRepository,
    )
    from backend.infrastructure.rendering.html_sanitizer import HtmlSanitizer
    from backend.infrastructure.versioning.github_sync_service import (
        GitHubSyncService,
    )

logger = logging.getLogger(__name__)


def publish_post_handler(
    command: PublishPostCommand,
    draft_repo: "FileSystemDraftRepository",
    post_repo: "PostRepository",
    markdown_service: "MarkdownRenderingService",
    html_sanitizer: "HtmlSanitizer",
    github_service: "GitHubSyncService",
) -> "Post":
    """Publish draft post: render, sanitize, persist, backup.

    Orchestrates the complete publishing workflow:
    1. Load Post aggregate from database and verify ownership
    2. Load draft from filesystem
    3. Render markdown to HTML (with Pygments syntax highlighting)
    4. Sanitize HTML with Bleach
    5. Update Post with rendered HTML via domain method
    6. Persist Post to database (atomic)
    7. Update draft front matter in filesystem (best-effort)
    8. Commit updated draft to GitHub (best-effort)

    Args:
        command: PublishPostCommand with slug, author_id, and user_role
        draft_repo: FileSystemDraftRepository for draft I/O
        post_repo: PostRepository for Post persistence
        markdown_service: MarkdownRenderingService for rendering
        html_sanitizer: HtmlSanitizer for sanitization
        github_service: GitHubSyncService for GitHub commits

    Returns:
        Post: Published Post aggregate with html_content set

    Raises:
        ValueError: If draft not found, user unauthorized, already published,
            post not in DB, or DB save fails
    """
    logger.debug(f"Loading Post from database: {command.slug}")
    post = post_repo.find_by_slug(command.slug)
    if post is None:
        raise ValueError(
            f"Post with slug '{command.slug}' not found in database. "
            "Create draft first via CreateDraftCommand"
        )

    if post.author_id != command.author_id and command.user_role != "admin":
        logger.warning(
            f"User {command.author_id} attempted to publish post "
            f"'{command.slug}' owned by user {post.author_id}"
        )
        raise ValueError("Cannot publish another author's post")

    logger.debug(f"Loading draft: {command.slug}")
    draft = draft_repo.find_by_slug(command.slug)
    if draft is None:
        raise ValueError(f"Draft with slug '{command.slug}' not found")

    if draft.published:
        raise ValueError(f"Post '{command.slug}' is already published")

    logger.info(f"Publishing post: {command.slug} - rendering markdown")
    html = markdown_service.render(draft.content)
    logger.debug(f"Rendered HTML for {command.slug}: {len(html)} bytes")

    logger.debug(f"Sanitizing HTML for {command.slug}")
    sanitized_html = html_sanitizer.sanitize(html)
    logger.debug(
        f"Sanitized HTML for {command.slug}: {len(sanitized_html)} bytes"
    )

    logger.debug(f"Calling post.publish() for {command.slug}")
    post.publish(sanitized_html)

    logger.info(f"Saving published post to database: {command.slug}")
    try:
        post = post_repo.save(post)
        logger.info(f"Post '{command.slug}' published to database")
    except (ValueError, Exception) as e:
        logger.error(f"Failed to save post to database: {command.slug}: {e}")
        raise

    try:
        logger.debug(f"Updating draft front matter: {command.slug}")
        draft.published = True
        draft.published_at = post.published_at
        draft_repo.save(draft)
        logger.debug(f"Updated draft front matter for {command.slug}")
    except OSError as e:
        logger.warning(
            f"Failed to update draft front matter for '{command.slug}': {e} - "
            "post is published, draft file state may be stale"
        )

    try:
        logger.debug(f"Committing to GitHub: drafts/{post.slug}.md")
        commit_message = f"Publish post: {draft.title}"
        commit_sha = github_service.commit_file(
            path=f"drafts/{post.slug}.md",
            content=draft.to_markdown(),
            message=commit_message,
        )
        if commit_sha is None:
            logger.warning(
                f"Failed to commit to GitHub for '{command.slug}' - "
                "post is published, GitHub out of sync"
            )
        else:
            logger.debug(f"Committed to GitHub with SHA: {commit_sha}")
    except Exception as e:
        logger.warning(
            f"Exception during GitHub commit for '{command.slug}': {e} - "
            "continuing"
        )

    return post
