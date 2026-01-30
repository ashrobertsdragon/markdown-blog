"""GitHub API synchronization service for draft version control.

This module provides the GitHubSyncService for committing and deleting draft
files via the GitHub Contents API with automatic retry logic and error handling.
Part of the Version Control bounded context infrastructure layer.
"""

import base64
import logging
import time
from typing import Any

import requests

logger = logging.getLogger(__name__)


class GitHubSyncService:
    """Sync draft files to GitHub with automatic retry and error handling.

    This service provides resilient GitHub API integration for version control
    operations on draft files. It handles authentication, file operations, rate
    limiting, and network errors without raising exceptions.

    Key behaviors:
    - Validates all constructor parameters (raises ValueError if empty)
    - Automatically retries on HTTP 429 with exponential backoff (1s, 2s, 4s)
    - Returns None/False on errors rather than raising exceptions
    - Logs all errors and retry attempts for debugging
    - Fetches existing file SHA before updates/deletes

    Attributes:
        _token: GitHub personal access token for authentication
        _owner: Repository owner username
        _repo: Repository name
        _base_url: GitHub API base URL
        _timeout: Request timeout in seconds
        _max_retries: Maximum retry attempts for rate limiting

    Example:
        >>> service = GitHubSyncService(
        ...     token="ghp_xxx",
        ...     owner="myuser",
        ...     repo="drafts"
        ... )
        >>> sha = service.commit_file(
        ...     path="drafts/post.md",
        ...     content="# Hello World",
        ...     message="Create new post"
        ... )
        >>> if sha:
        ...     print(f"Committed with SHA: {sha}")
    """

    def __init__(self, token: str, owner: str, repo: str) -> None:
        """Initialize GitHub sync service with repository credentials.

        Args:
            token: GitHub personal access token
            owner: GitHub repository owner username
            repo: GitHub repository name

        Raises:
            ValueError: If token, owner, or repo is empty string
        """
        if not token:
            raise ValueError("GitHub token cannot be empty")
        if not owner:
            raise ValueError("Repository owner cannot be empty")
        if not repo:
            raise ValueError("Repository name cannot be empty")

        self._token = token
        self._owner = owner
        self._repo = repo
        self._base_url = "https://api.github.com"
        self._timeout = 5
        self._max_retries = 3

    def commit_file(self, path: str, content: str, message: str) -> str | None:
        r"""Commit a file to the repository (create or update).

        Creates a new file or updates an existing file at the specified path.
        Automatically fetches the current file SHA if the file exists to
        enable updates. Retries on rate limiting with exponential backoff.

        Args:
            path: File path in repository (e.g., "drafts/post.md")
            content: File content to commit (will be base64 encoded)
            message: Commit message

        Returns:
            Commit SHA string on success, None on failure

        Example:
            >>> sha = service.commit_file(
            ...     path="drafts/my-post.md",
            ...     content="# My Post\n\nContent here",
            ...     message="Update post"
            ... )
            >>> if sha:
            ...     print(f"Success: {sha}")
            ... else:
            ...     print("Commit failed")
        """
        file_sha = self._get_file_sha(path)
        encoded_content = base64.b64encode(content.encode()).decode()

        url = (
            f"{self._base_url}/repos/{self._owner}/{self._repo}/contents/{path}"
        )
        headers = {
            "Authorization": f"Bearer {self._token}",
            "Accept": "application/vnd.github.v3+json",
        }

        payload: dict[str, Any] = {
            "message": message,
            "content": encoded_content,
        }

        if file_sha:
            payload["sha"] = file_sha

        return self._execute_put_with_retry(url, headers, payload, path)

    def _execute_put_with_retry(
        self,
        url: str,
        headers: dict[str, str],
        payload: dict[str, Any],
        path: str,
    ) -> str | None:
        """Execute PUT request with retry logic for rate limiting.

        Retries up to max_retries times on HTTP 429 with exponential backoff.
        Handles network errors gracefully without raising exceptions.

        Args:
            url: GitHub API endpoint URL
            headers: Request headers including authorization
            payload: Request body data
            path: File path for logging purposes

        Returns:
            Commit SHA string on success, None on failure
        """
        for attempt in range(self._max_retries):
            try:
                response = requests.put(
                    url, json=payload, headers=headers, timeout=self._timeout
                )

                if response.status_code == 429:
                    delay = 2**attempt
                    max_retries = self._max_retries
                    logger.warning(
                        f"Rate limited. Retry attempt {attempt + 1}/"
                        f"{max_retries} after {delay}s delay"
                    )
                    time.sleep(delay)
                    continue

                if response.status_code in (200, 201):
                    commit_sha: str = response.json()["commit"]["sha"]
                    logger.info(f"Successfully committed {path}: {commit_sha}")
                    return commit_sha

                logger.error(
                    f"GitHub API error {response.status_code} for {path}: "
                    f"{response.text}"
                )
                return None

            except requests.exceptions.Timeout:
                logger.error(f"Timeout while committing {path}")
                return None
            except requests.exceptions.ConnectionError as exc:
                logger.error(f"Connection error while committing {path}: {exc}")
                return None
            except requests.exceptions.RequestException as exc:
                logger.error(f"Request error while committing {path}: {exc}")
                return None
            except (KeyError, ValueError) as exc:
                logger.error(
                    f"Data parsing error while committing {path}: {exc}"
                )
                return None

        logger.error(
            f"Exhausted all {self._max_retries} retry attempts for {path}"
        )
        return None

    def delete_file(self, path: str, message: str) -> bool:
        """Delete a file from the repository.

        Fetches the current file SHA and then deletes the file. Returns False
        if the file doesn't exist rather than treating it as an error.

        Args:
            path: File path in repository to delete
            message: Commit message for the deletion

        Returns:
            True on successful deletion, False on failure or if file not found

        Example:
            >>> success = service.delete_file(
            ...     path="drafts/old-post.md",
            ...     message="Remove outdated post"
            ... )
            >>> if success:
            ...     print("File deleted")
        """
        file_sha = self._get_file_sha(path)

        if not file_sha:
            logger.warning(f"Cannot delete {path}: file not found")
            return False

        url = (
            f"{self._base_url}/repos/{self._owner}/{self._repo}/contents/{path}"
        )
        headers = {
            "Authorization": f"Bearer {self._token}",
            "Accept": "application/vnd.github.v3+json",
        }

        payload = {
            "message": message,
            "sha": file_sha,
        }

        try:
            response = requests.delete(
                url, json=payload, headers=headers, timeout=self._timeout
            )

            if response.status_code == 200:
                logger.info(f"Successfully deleted {path}")
                return True

            status = response.status_code
            logger.error(
                f"GitHub API error {status} while deleting {path}: "
                f"{response.text}"
            )
            return False

        except requests.exceptions.Timeout:
            logger.error(f"Timeout while deleting {path}")
            return False
        except requests.exceptions.ConnectionError as exc:
            logger.error(f"Connection error while deleting {path}: {exc}")
            return False
        except requests.exceptions.RequestException as exc:
            logger.error(f"Request error while deleting {path}: {exc}")
            return False
        except (KeyError, ValueError) as exc:
            logger.error(f"Data parsing error while deleting {path}: {exc}")
            return False

    def get_file_content(self, path: str) -> str | None:
        """Fetch file content from GitHub repository.

        Retrieves the current content of a file from GitHub, decoding it
        from base64. Used for corruption recovery to restore files from
        version control.

        Args:
            path: File path in repository (e.g., "drafts/my-post.md")

        Returns:
            File content string if successful, None on failure

        Example:
            >>> content = service.get_file_content("drafts/post.md")
            >>> if content:
            ...     print("Recovered content from GitHub")
        """
        url = (
            f"{self._base_url}/repos/{self._owner}/{self._repo}/contents/{path}"
        )
        headers = {
            "Authorization": f"Bearer {self._token}",
            "Accept": "application/vnd.github.v3+json",
        }

        try:
            response = requests.get(url, headers=headers, timeout=self._timeout)

            if response.status_code == 200:
                encoded_content: str = response.json()["content"]
                decoded_content = base64.b64decode(encoded_content).decode()
                logger.info(f"Successfully fetched content for {path}")
                return decoded_content

            if response.status_code == 404:
                logger.warning(f"File {path} not found in GitHub")
                return None

            status = response.status_code
            logger.error(
                f"GitHub API error {status} fetching content for {path}: "
                f"{response.text}"
            )
            return None

        except requests.exceptions.Timeout:
            logger.error(f"Timeout while fetching content for {path}")
            return None
        except requests.exceptions.ConnectionError as exc:
            logger.error(
                f"Connection error while fetching content for {path}: {exc}"
            )
            return None
        except requests.exceptions.RequestException as exc:
            logger.error(
                f"Request error while fetching content for {path}: {exc}"
            )
            return None
        except (KeyError, ValueError) as exc:
            logger.error(
                f"Data parsing error while fetching content for {path}: {exc}"
            )
            return None

    def _get_file_sha(self, path: str) -> str | None:
        """Fetch the current SHA of a file in the repository.

        Used internally to get the file SHA required for updates and deletions.
        Returns None if the file doesn't exist (404).

        Args:
            path: File path in repository

        Returns:
            File SHA string if file exists, None if file not found or on error
        """
        url = (
            f"{self._base_url}/repos/{self._owner}/{self._repo}/contents/{path}"
        )
        headers = {
            "Authorization": f"Bearer {self._token}",
            "Accept": "application/vnd.github.v3+json",
        }

        try:
            response = requests.get(url, headers=headers, timeout=self._timeout)

            if response.status_code == 200:
                file_sha: str = response.json()["sha"]
                return file_sha

            if response.status_code == 404:
                logger.debug(f"File {path} does not exist (will create new)")
                return None

            status = response.status_code
            logger.warning(
                f"Unexpected status {status} fetching SHA for {path}"
            )
            return None

        except requests.exceptions.Timeout:
            logger.error(f"Timeout while fetching SHA for {path}")
            return None
        except requests.exceptions.ConnectionError as exc:
            logger.error(
                f"Connection error while fetching SHA for {path}: {exc}"
            )
            return None
        except requests.exceptions.RequestException as exc:
            logger.error(f"Request error while fetching SHA for {path}: {exc}")
            return None
        except (KeyError, ValueError) as exc:
            logger.error(
                f"Data parsing error while fetching SHA for {path}: {exc}"
            )
            return None
