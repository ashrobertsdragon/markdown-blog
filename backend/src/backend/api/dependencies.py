"""Dependency injection for API routes."""

import logging
import os
from typing import cast

from backend.config import FileSystemSettings, GitHubSettings
from backend.domain.protocols.services import (
    DiffService as DiffServiceProtocol,
)
from backend.domain.protocols.services import (
    HtmlSanitizer as HtmlSanitizerProtocol,
)
from backend.domain.protocols.services import (
    MarkdownService as MarkdownServiceProtocol,
)
from backend.infrastructure.markdown.markdown_rendering_service import (
    MarkdownRenderingService,
)
from backend.infrastructure.persistence.filesystem_draft_repository import (
    FileSystemDraftRepository,
)
from backend.infrastructure.persistence.post_repository import PostRepository
from backend.infrastructure.persistence.post_revision_repository import (
    PostRevisionRepository,
)
from backend.infrastructure.rendering.html_sanitizer import HtmlSanitizer
from backend.infrastructure.versioning.diff_service import DiffService
from backend.infrastructure.versioning.github_sync_service import (
    GitHubSyncService,
)
from backend.infrastructure.versioning.mock_github_service import (
    MockGitHubSyncService,
)

logger = logging.getLogger(__name__)

_filesystem_settings: FileSystemSettings | None = None
_github_settings: GitHubSettings | None = None
_github_service: GitHubSyncService | MockGitHubSyncService | None = None


def get_filesystem_settings() -> FileSystemSettings:
    """Lazily initialize FileSystemSettings instance."""
    global _filesystem_settings
    if _filesystem_settings is None:
        _filesystem_settings = FileSystemSettings()
    return _filesystem_settings


def get_github_settings() -> GitHubSettings:
    """Lazily initialize GitHubSettings instance."""
    global _github_settings
    if _github_settings is None:
        _github_settings = GitHubSettings()
    return _github_settings


def get_post_repository() -> PostRepository:
    """Get PostRepository instance."""
    return PostRepository()


def get_revision_repository() -> PostRevisionRepository:
    """Get PostRevisionRepository instance."""
    return PostRevisionRepository()


def get_draft_repository() -> FileSystemDraftRepository:
    """Get FileSystemDraftRepository instance."""
    fs_settings = get_filesystem_settings()
    return FileSystemDraftRepository(fs_settings.DRAFTS_PATH)


def get_github_service() -> GitHubSyncService | MockGitHubSyncService:
    """Get GitHubSyncService instance (or mock in TESTING environment)."""
    global _github_service
    if _github_service is not None:
        return _github_service

    gh_settings = get_github_settings()
    flask_env = os.environ.get("FLASK_ENV")

    if flask_env == "TESTING":
        logger.info("Using MockGitHubSyncService for TESTING environment")
        _github_service = MockGitHubSyncService(
            gh_settings.GITHUB_TOKEN,
            gh_settings.GITHUB_OWNER,
            gh_settings.GITHUB_REPO,
        )
    else:
        _github_service = GitHubSyncService(
            gh_settings.GITHUB_TOKEN,
            gh_settings.GITHUB_OWNER,
            gh_settings.GITHUB_REPO,
        )
    return _github_service


def get_markdown_service() -> MarkdownServiceProtocol:
    """Get MarkdownService instance with protocol type."""
    return cast(MarkdownServiceProtocol, MarkdownRenderingService())


def get_sanitizer() -> HtmlSanitizerProtocol:
    """Get HtmlSanitizer instance with protocol type."""
    return cast(HtmlSanitizerProtocol, HtmlSanitizer())


def get_diff_service() -> DiffServiceProtocol:
    """Get DiffService instance with protocol type."""
    return cast(DiffServiceProtocol, DiffService())
