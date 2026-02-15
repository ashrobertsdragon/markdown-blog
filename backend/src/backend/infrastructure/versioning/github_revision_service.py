"""GitHub API revision service for fetching commit history.

This module provides the GitHubRevisionService for retrieving commit history
and file content at specific commits via the GitHub API with automatic retry
logic and error handling. Part of the Version Control bounded context
infrastructure layer.
"""

import base64
import logging
import time
from typing import Any

import requests

logger = logging.getLogger(__name__)


class GitHubRevisionService:
    """Fetch revision history from GitHub with retry and error handling.

    This service provides resilient GitHub API integration for retrieving
    commit history and file content at specific revisions. It handles
    authentication, rate limiting, and network errors without raising
    exceptions.

    Key behaviors:
    - Validates all constructor parameters (raises ValueError if empty)
    - Automatically retries on HTTP 429 with exponential backoff (1s, 2s, 4s)
    - Returns None/empty list on errors rather than raising exceptions
    - Logs all errors and retry attempts for debugging
    - Returns empty list on 404 for commits (file doesn't exist)

    Attributes:
        _token: GitHub personal access token for authentication
        _owner: Repository owner username
        _repo: Repository name
        _base_url: GitHub API base URL
        _timeout: Request timeout in seconds
        _max_retries: Maximum retry attempts for rate limiting

    Example:
        >>> service = GitHubRevisionService(
        ...     token="ghp_xxx",
        ...     owner="myuser",
        ...     repo="drafts"
        ... )
        >>> commits = service.fetch_commits(
        ...     owner="myuser",
        ...     repo="drafts",
        ...     path="drafts/post.md"
        ... )
        >>> if commits:
        ...     print(f"Found {len(commits)} commits")
    """

    def __init__(self, token: str, owner: str, repo: str) -> None:
        """Initialize GitHub revision service with repository credentials.

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

    def fetch_commits(
        self, owner: str, repo: str, path: str, limit: int = 50
    ) -> list[dict[str, Any]] | None:
        """Fetch commit history for a file from GitHub API.

        Retrieves the commit history for a specific file path with
        pagination support. Retries on rate limiting with exponential
        backoff.

        Args:
            owner: Repository owner username
            repo: Repository name
            path: File path in repository (e.g., "drafts/post.md")
            limit: Maximum number of commits to fetch (default: 50)

        Returns:
            List of commit dictionaries on success, empty list if file
            not found (404), None on other errors

        Example:
            >>> commits = service.fetch_commits(
            ...     owner="myuser",
            ...     repo="drafts",
            ...     path="drafts/my-post.md",
            ...     limit=25
            ... )
            >>> if commits:
            ...     for commit in commits:
            ...         print(commit["sha"])
        """
        url = f"{self._base_url}/repos/{owner}/{repo}/commits"
        headers = self._get_headers()
        params: dict[str, str | int] = {"path": path, "per_page": limit}

        for attempt in range(self._max_retries):
            try:
                response = requests.get(
                    url, headers=headers, params=params, timeout=self._timeout
                )

                if response.status_code == 429:
                    delay = 2**attempt
                    logger.warning(
                        f"Rate limited. Retry attempt {attempt + 1}/"
                        f"{self._max_retries} after {delay}s delay"
                    )
                    time.sleep(delay)
                    continue

                if response.status_code == 200:
                    commits: list[dict[str, Any]] = response.json()
                    logger.info(
                        f"Successfully fetched {len(commits)} commits for "
                        f"{path}"
                    )
                    return commits

                if response.status_code == 404:
                    logger.warning(f"File {path} not found in GitHub")
                    return []

                logger.error(
                    f"GitHub API error {response.status_code} for {path}: "
                    f"{response.text}"
                )
                return None

            except requests.exceptions.Timeout:
                logger.error(f"Timeout while fetching commits for {path}")
                return None
            except requests.exceptions.ConnectionError as exc:
                logger.error(
                    f"Connection error while fetching commits for {path}: {exc}"
                )
                return None
            except requests.exceptions.RequestException as exc:
                logger.error(
                    f"Request error while fetching commits for {path}: {exc}"
                )
                return None
            except (KeyError, ValueError) as exc:
                logger.error(
                    f"Data parsing error while fetching commits for {path}: "
                    f"{exc}"
                )
                return None

        logger.error(
            f"Exhausted all {self._max_retries} retry attempts for {path}"
        )
        return None

    def fetch_file_at_sha(
        self, owner: str, repo: str, path: str, sha: str
    ) -> str | None:
        """Fetch file content at specific commit SHA from GitHub API.

        Retrieves the content of a file at a specific commit revision,
        decoding it from base64 encoding.

        Args:
            owner: Repository owner username
            repo: Repository name
            path: File path in repository (e.g., "drafts/post.md")
            sha: Git commit SHA to retrieve

        Returns:
            File content string if successful, None on failure

        Example:
            >>> content = service.fetch_file_at_sha(
            ...     owner="myuser",
            ...     repo="drafts",
            ...     path="drafts/post.md",
            ...     sha="abc123def456..."
            ... )
            >>> if content:
            ...     print("Retrieved content from revision")
        """
        url = f"{self._base_url}/repos/{owner}/{repo}/contents/{path}"
        headers = self._get_headers()
        params = {"ref": sha}

        try:
            response = requests.get(
                url, headers=headers, params=params, timeout=self._timeout
            )

            if response.status_code == 200:
                encoded_content: str = response.json()["content"]
                decoded_content = base64.b64decode(encoded_content).decode()
                logger.info(
                    f"Successfully fetched content for {path} at SHA {sha}"
                )
                return decoded_content

            if response.status_code == 404:
                logger.warning(f"File {path} at SHA {sha} not found in GitHub")
                return None

            logger.error(
                f"GitHub API error {response.status_code} fetching "
                f"content for {path} at SHA {sha}: {response.text}"
            )
            return None

        except requests.exceptions.Timeout:
            logger.error(
                f"Timeout while fetching content for {path} at SHA {sha}"
            )
            return None
        except requests.exceptions.ConnectionError as exc:
            logger.error(
                f"Connection error while fetching content for {path} at "
                f"SHA {sha}: {exc}"
            )
            return None
        except requests.exceptions.RequestException as exc:
            logger.error(
                f"Request error while fetching content for {path} at "
                f"SHA {sha}: {exc}"
            )
            return None
        except (KeyError, ValueError, Exception) as exc:
            logger.error(
                f"Data parsing error while fetching content for {path} at "
                f"SHA {sha}: {exc}"
            )
            return None

    def _get_headers(self) -> dict[str, str]:
        """Return authentication headers for GitHub API requests.

        Returns:
            Dictionary with Authorization and Accept headers
        """
        return {
            "Authorization": f"Bearer {self._token}",
            "Accept": "application/vnd.github.v3+json",
        }
