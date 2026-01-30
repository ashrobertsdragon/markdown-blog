"""Handler for SaveDraftCommand.

This module implements the handler function that orchestrates the draft
save workflow with corruption recovery support.
"""

import logging
from datetime import UTC, datetime

import yaml

from backend.application.commands.save_draft_command import SaveDraftCommand
from backend.infrastructure.persistence.filesystem_draft_repository import (
    DraftFile,
    FileSystemDraftRepository,
)
from backend.infrastructure.versioning.github_sync_service import (
    GitHubSyncService,
)

logger = logging.getLogger(__name__)


def save_draft_handler(
    command: SaveDraftCommand,
    draft_repo: FileSystemDraftRepository,
    github_service: GitHubSyncService,
) -> None:
    """Handle SaveDraftCommand to update draft content.

    Orchestrates workflow:
    1. Find existing draft file
    2. Update content, preserve front matter
    3. Save to filesystem
    4. Commit to GitHub (continues on failure)

    Corruption recovery:
    - If file corrupted, fetch from GitHub
    - If GitHub recovery fails, create new draft with defaults
    - Logs all recovery attempts

    Args:
        command: SaveDraftCommand with slug and content
        draft_repo: FileSystemDraftRepository for file operations
        github_service: GitHubSyncService for version control

    Raises:
        ValueError: If draft not found (NotFoundError)
        ValueError: If slug is invalid
        ValueError: If corruption recovery fails completely
    """
    try:
        draft = draft_repo.find_by_slug(command.slug)
    except (ValueError, yaml.YAMLError, AttributeError) as e:
        logger.error(
            f"Corrupted draft file '{command.slug}': {e}. "
            "Attempting recovery..."
        )
        draft = _recover_from_corruption(
            command.slug, draft_repo, github_service
        )

    if draft is None:
        raise ValueError(f"Draft with slug '{command.slug}' not found")

    draft.content = command.content

    draft_repo.save(draft)

    commit_message = f"Update draft: {draft.title}"
    commit_sha = github_service.commit_file(
        path=f"drafts/{command.slug}.md",
        content=draft.to_markdown(),
        message=commit_message,
    )

    if commit_sha is None:
        logger.warning(
            f"Failed to commit draft '{draft.slug}' to GitHub, "
            "continuing with local save"
        )


def _recover_from_corruption(
    slug: str,
    draft_repo: FileSystemDraftRepository,
    github_service: GitHubSyncService,
) -> DraftFile:
    """Recover corrupted draft file from GitHub.

    Recovery strategy:
    1. Fetch latest version from GitHub
    2. Parse and return DraftFile
    3. If GitHub fails, create new draft with defaults

    Args:
        slug: Draft identifier
        draft_repo: Repository for saving recovered file
        github_service: Service for fetching from GitHub

    Returns:
        Recovered or newly created DraftFile

    Raises:
        ValueError: If recovery fails completely
    """
    logger.info(f"Attempting GitHub recovery for '{slug}'")

    content = github_service.get_file_content(f"drafts/{slug}.md")

    if content is not None:
        try:
            draft = DraftFile.from_markdown(content, slug=slug)
            draft_repo.save(draft)
            logger.info(f"Successfully recovered '{slug}' from GitHub")
            return draft
        except (ValueError, yaml.YAMLError, AttributeError) as e:
            logger.error(
                f"Failed to parse recovered content for '{slug}': {e}. "
                "Creating new draft with defaults"
            )

    logger.warning(f"File '{slug}' not found in GitHub")

    new_draft = DraftFile(
        slug=slug,
        title=f"Recovered: {slug}",
        author="unknown",
        content="",
        published=False,
        created_at=datetime.now(UTC),
    )

    draft_repo.save(new_draft)

    logger.warning(
        f"Creating new draft file for '{slug}' with default front matter"
    )

    return new_draft
