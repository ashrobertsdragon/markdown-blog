"""Mock GitHub synchronization service for testing.

Provides an in-memory or filesystem-based mock of GitHubSyncService to avoid
real network calls during E2E and unit testing.
"""

import logging
import uuid

logger = logging.getLogger(__name__)


class MockGitHubSyncService:
    """Mock implementation of GitHubSyncService.

    Simulates GitHub file operations in-memory.
    """

    def __init__(self, token: str, owner: str, repo: str) -> None:
        """Initialize MockGitHubSyncService with repository credentials.

        Args:
            token: GitHub personal access token
            owner: GitHub repository owner username
            repo: GitHub repository name
        """
        self._token = token
        self._owner = owner
        self._repo = repo
        # Simple in-memory store: {path: content}
        self._files: dict[str, str] = {}

    def commit_file(self, path: str, content: str, message: str) -> str | None:
        """Simulate committing a file."""
        self._files[path] = content
        # Return a fake 40-char SHA (hex is 32, so we pad with zeros)
        fake_sha = uuid.uuid4().hex.zfill(40)
        logger.info(f"[MOCK GITHUB] Committed {path} with message: {message}")
        return fake_sha

    def delete_file(self, path: str, message: str) -> bool:
        """Simulate deleting a file."""
        if path in self._files:
            del self._files[path]
            logger.info(f"[MOCK GITHUB] Deleted {path} with message: {message}")
            return True
        logger.warning(f"[MOCK GITHUB] Failed to delete {path}: not found")
        return False

    def get_file_content(self, path: str) -> str | None:
        """Simulate fetching file content."""
        content = self._files.get(path)
        if content is not None:
            logger.info(f"[MOCK GITHUB] Fetched content for {path}")
            return content
        logger.warning(f"[MOCK GITHUB] File {path} not found")
        return None

    def _get_file_sha(self, path: str) -> str | None:
        """Simulate fetching file SHA."""
        if path in self._files:
            return "mock_sha_existing"
        return None
