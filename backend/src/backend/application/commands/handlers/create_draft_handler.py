"""Handler for CreateDraftCommand.

This module implements the handler function that orchestrates the draft
creation workflow across repositories and external services.
"""

import logging

from backend.application.commands.create_draft_command import CreateDraftCommand
from backend.domain.aggregates.post import Post
from backend.infrastructure.persistence.filesystem_draft_repository import (
    DraftFile,
    FileSystemDraftRepository,
)
from backend.infrastructure.persistence.post_repository import PostRepository
from backend.infrastructure.versioning.github_sync_service import (
    GitHubSyncService,
)

logger = logging.getLogger(__name__)


def create_draft_handler(
    command: CreateDraftCommand,
    draft_repo: FileSystemDraftRepository,
    post_repo: PostRepository,
    github_service: GitHubSyncService,
) -> Post:
    """Handle CreateDraftCommand to create a new draft post.

    Orchestrates the complete draft creation workflow:
    1. Validates slug uniqueness in database
    2. Validates slug uniqueness in filesystem
    3. Creates Post aggregate via domain logic
    4. Saves draft file to filesystem with YAML front matter
    5. Commits to GitHub (continues on failure)
    6. Persists Post to database
    7. Returns created Post

    Args:
        command: CreateDraftCommand with slug, title, author_id
        draft_repo: FileSystemDraftRepository for draft file operations
        post_repo: PostRepository for database operations
        github_service: GitHubSyncService for version control

    Returns:
        Post: Created draft post aggregate

    Raises:
        ValueError: If slug already exists in database or filesystem
        ValueError: If domain validation fails (empty title, invalid
            author_id, invalid slug)
    """
    if post_repo.find_by_slug(command.slug) is not None:
        raise ValueError(f"Post with slug '{command.slug}' already exists")

    if draft_repo.find_by_slug(command.slug) is not None:
        raise ValueError(f"Draft with slug '{command.slug}' already exists")

    post = Post.create_draft(
        slug=command.slug, title=command.title, author_id=command.author_id
    )

    draft_file = DraftFile(
        slug=str(post.slug),
        title=post.title,
        author=str(command.author_id),
        content="",
        published=False,
        created_at=post.created_at,
    )

    draft_repo.save(draft_file)

    commit_message = f"Create draft: {post.title}"
    commit_sha = github_service.commit_file(
        path=f"drafts/{post.slug}.md",
        content=draft_file.to_markdown(),
        message=commit_message,
    )

    if commit_sha is None:
        logger.warning(
            f"Failed to commit draft '{post.slug}' to GitHub, "
            "continuing with local save"
        )

    try:
        post_repo.save(post)
    except Exception:
        logger.error(
            f"Failed to save post '{post.slug}' to database, "
            "rolling back filesystem changes"
        )
        draft_repo.delete(str(post.slug))
        raise

    return post
