"""Unit tests for GitHubRevisionService using strict TDD methodology.

This test suite follows red-green-refactor cycles to implement GitHub revision
integration with comprehensive error handling and rate limiting.
"""

import base64
from unittest.mock import Mock, patch

import pytest
import requests
from backend.infrastructure.versioning.github_revision_service import (
    GitHubRevisionService,
)


class TestGitHubRevisionServiceInitialization:
    """Test suite for GitHubRevisionService constructor validation."""

    def test_init_with_valid_credentials(self) -> None:
        """Initialize service with valid token, owner, and repo."""
        service = GitHubRevisionService(
            token="ghp_validtoken123", owner="testowner", repo="testrepo"
        )

        assert service._token == "ghp_validtoken123"
        assert service._owner == "testowner"
        assert service._repo == "testrepo"
        assert service._base_url == "https://api.github.com"
        assert service._timeout == 5
        assert service._max_retries == 3

    def test_init_with_empty_token_raises_value_error(self) -> None:
        """Raise ValueError when token is empty string."""
        with pytest.raises(ValueError, match="GitHub token cannot be empty"):
            GitHubRevisionService(token="", owner="owner", repo="repo")

    def test_init_with_empty_owner_raises_value_error(self) -> None:
        """Raise ValueError when owner is empty string."""
        with pytest.raises(
            ValueError, match="Repository owner cannot be empty"
        ):
            GitHubRevisionService(token="ghp_token", owner="", repo="repo")

    def test_init_with_empty_repo_raises_value_error(self) -> None:
        """Raise ValueError when repo is empty string."""
        with pytest.raises(ValueError, match="Repository name cannot be empty"):
            GitHubRevisionService(token="ghp_token", owner="owner", repo="")


class TestFetchCommits:
    """Test suite for fetch_commits method with GitHub API integration."""

    @pytest.fixture
    def service(self) -> GitHubRevisionService:
        """Create GitHubRevisionService instance for testing."""
        return GitHubRevisionService(
            token="ghp_testtoken", owner="testowner", repo="testrepo"
        )

    @patch(
        "backend.infrastructure.versioning.github_revision_service.requests.get"
    )
    def test_fetch_commits_success_returns_commit_list(
        self, mock_get: Mock, service: GitHubRevisionService
    ) -> None:
        """Fetch commits returns list of commit dictionaries on 200 response."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = [
            {
                "sha": "abc123" * 7,
                "commit": {
                    "author": {
                        "name": "Test Author",
                        "email": "test@example.com",
                        "date": "2026-02-13T10:00:00Z",
                    },
                    "message": "Initial commit",
                },
            },
            {
                "sha": "def456" * 7,
                "commit": {
                    "author": {
                        "name": "Another Author",
                        "email": "another@example.com",
                        "date": "2026-02-12T15:30:00Z",
                    },
                    "message": "Update post",
                },
            },
        ]
        mock_get.return_value = mock_response

        result = service.fetch_commits(
            owner="testowner", repo="testrepo", path="drafts/test.md"
        )

        assert result is not None
        assert len(result) == 2
        assert result[0]["sha"] == "abc123" * 7
        assert result[0]["commit"]["author"]["name"] == "Test Author"
        assert result[0]["commit"]["message"] == "Initial commit"

        mock_get.assert_called_once()
        args, kwargs = mock_get.call_args
        assert "repos/testowner/testrepo/commits" in args[0]
        assert kwargs["params"] == {"path": "drafts/test.md", "per_page": 50}
        assert kwargs["timeout"] == 5

    @patch(
        "backend.infrastructure.versioning.github_revision_service.requests.get"
    )
    def test_fetch_commits_respects_limit_parameter(
        self, mock_get: Mock, service: GitHubRevisionService
    ) -> None:
        """Fetch commits respects the limit parameter in API request."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = []
        mock_get.return_value = mock_response

        service.fetch_commits(
            owner="testowner", repo="testrepo", path="drafts/test.md", limit=25
        )

        args, kwargs = mock_get.call_args
        assert kwargs["params"]["per_page"] == 25

    @patch(
        "backend.infrastructure.versioning.github_revision_service.requests.get"
    )
    def test_fetch_commits_on_404_returns_empty_list(
        self, mock_get: Mock, service: GitHubRevisionService
    ) -> None:
        """Fetch commits returns empty list when file not found (404)."""
        mock_response = Mock()
        mock_response.status_code = 404
        mock_get.return_value = mock_response

        result = service.fetch_commits(
            owner="testowner", repo="testrepo", path="drafts/nonexistent.md"
        )

        assert result == []

    @patch(
        "backend.infrastructure.versioning.github_revision_service.requests.get"
    )
    def test_fetch_commits_on_non_200_non_404_returns_none(
        self, mock_get: Mock, service: GitHubRevisionService
    ) -> None:
        """Fetch commits returns None on non-200/404 status codes."""
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"
        mock_get.return_value = mock_response

        result = service.fetch_commits(
            owner="testowner", repo="testrepo", path="drafts/test.md"
        )

        assert result is None

    @patch(
        "backend.infrastructure.versioning.github_revision_service.time.sleep"
    )
    @patch(
        "backend.infrastructure.versioning.github_revision_service.requests.get"
    )
    def test_fetch_commits_retries_on_429_with_exponential_backoff(
        self, mock_get: Mock, mock_sleep: Mock, service: GitHubRevisionService
    ) -> None:
        """Retry on 429 with exponential backoff (1s, 2s, 4s)."""
        mock_response_429 = Mock()
        mock_response_429.status_code = 429

        mock_response_200 = Mock()
        mock_response_200.status_code = 200
        mock_response_200.json.return_value = [{"sha": "abc123" * 7}]

        mock_get.side_effect = [
            mock_response_429,
            mock_response_429,
            mock_response_200,
        ]

        result = service.fetch_commits(
            owner="testowner", repo="testrepo", path="drafts/test.md"
        )

        assert result is not None
        assert len(result) == 1
        assert mock_get.call_count == 3
        assert mock_sleep.call_count == 2
        mock_sleep.assert_any_call(1)
        mock_sleep.assert_any_call(2)

    @patch(
        "backend.infrastructure.versioning.github_revision_service.time.sleep"
    )
    @patch(
        "backend.infrastructure.versioning.github_revision_service.requests.get"
    )
    def test_fetch_commits_exhausts_retries_on_persistent_429(
        self, mock_get: Mock, mock_sleep: Mock, service: GitHubRevisionService
    ) -> None:
        """Fetch commits returns None after exhausting all retries on 429."""
        mock_response = Mock()
        mock_response.status_code = 429
        mock_get.return_value = mock_response

        result = service.fetch_commits(
            owner="testowner", repo="testrepo", path="drafts/test.md"
        )

        assert result is None
        assert mock_get.call_count == 3
        assert mock_sleep.call_count == 3
        mock_sleep.assert_any_call(1)
        mock_sleep.assert_any_call(2)
        mock_sleep.assert_any_call(4)

    @patch(
        "backend.infrastructure.versioning.github_revision_service.requests.get"
    )
    def test_fetch_commits_handles_timeout_gracefully(
        self, mock_get: Mock, service: GitHubRevisionService
    ) -> None:
        """Fetch commits returns None on request timeout."""
        mock_get.side_effect = requests.exceptions.Timeout()

        result = service.fetch_commits(
            owner="testowner", repo="testrepo", path="drafts/test.md"
        )

        assert result is None

    @patch(
        "backend.infrastructure.versioning.github_revision_service.requests.get"
    )
    def test_fetch_commits_handles_connection_error_gracefully(
        self, mock_get: Mock, service: GitHubRevisionService
    ) -> None:
        """Fetch commits returns None on connection error."""
        mock_get.side_effect = requests.exceptions.ConnectionError()

        result = service.fetch_commits(
            owner="testowner", repo="testrepo", path="drafts/test.md"
        )

        assert result is None

    @patch(
        "backend.infrastructure.versioning.github_revision_service.requests.get"
    )
    def test_fetch_commits_handles_json_parse_error_gracefully(
        self, mock_get: Mock, service: GitHubRevisionService
    ) -> None:
        """Fetch commits returns None when JSON parsing fails."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.side_effect = ValueError("Invalid JSON")
        mock_get.return_value = mock_response

        result = service.fetch_commits(
            owner="testowner", repo="testrepo", path="drafts/test.md"
        )

        assert result is None

    @patch(
        "backend.infrastructure.versioning.github_revision_service.requests.get"
    )
    def test_fetch_commits_includes_auth_headers(
        self, mock_get: Mock, service: GitHubRevisionService
    ) -> None:
        """Fetch commits includes proper authentication headers."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = []
        mock_get.return_value = mock_response

        service.fetch_commits(
            owner="testowner", repo="testrepo", path="drafts/test.md"
        )

        args, kwargs = mock_get.call_args
        assert kwargs["headers"]["Authorization"] == "Bearer ghp_testtoken"
        assert kwargs["headers"]["Accept"] == "application/vnd.github.v3+json"


class TestFetchFileAtSha:
    """Test suite for fetch_file_at_sha method with content retrieval."""

    @pytest.fixture
    def service(self) -> GitHubRevisionService:
        """Create GitHubRevisionService instance for testing."""
        return GitHubRevisionService(
            token="ghp_testtoken", owner="testowner", repo="testrepo"
        )

    @patch(
        "backend.infrastructure.versioning.github_revision_service.requests.get"
    )
    def test_fetch_file_at_sha_success_returns_decoded_content(
        self, mock_get: Mock, service: GitHubRevisionService
    ) -> None:
        """Fetch file at SHA returns base64-decoded content on 200 response."""
        content = "# Test Post\n\nThis is test content."
        encoded_content = base64.b64encode(content.encode()).decode()

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "content": encoded_content,
            "sha": "abc123" * 7,
        }
        mock_get.return_value = mock_response

        result = service.fetch_file_at_sha(
            owner="testowner",
            repo="testrepo",
            path="drafts/test.md",
            sha="abc123" * 7,
        )

        assert result == content
        mock_get.assert_called_once()
        args, kwargs = mock_get.call_args
        assert "repos/testowner/testrepo/contents/drafts/test.md" in args[0]
        assert kwargs["params"] == {"ref": "abc123" * 7}

    @patch(
        "backend.infrastructure.versioning.github_revision_service.requests.get"
    )
    def test_fetch_file_at_sha_on_404_returns_none(
        self, mock_get: Mock, service: GitHubRevisionService
    ) -> None:
        """Fetch file at SHA returns None when SHA not found (404)."""
        mock_response = Mock()
        mock_response.status_code = 404
        mock_get.return_value = mock_response

        result = service.fetch_file_at_sha(
            owner="testowner",
            repo="testrepo",
            path="drafts/test.md",
            sha="nonexistent",
        )

        assert result is None

    @patch(
        "backend.infrastructure.versioning.github_revision_service.requests.get"
    )
    def test_fetch_file_at_sha_handles_base64_decode_error(
        self, mock_get: Mock, service: GitHubRevisionService
    ) -> None:
        """Fetch file at SHA returns None on base64 decoding error."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"content": "invalid-base64!!!"}
        mock_get.return_value = mock_response

        result = service.fetch_file_at_sha(
            owner="testowner",
            repo="testrepo",
            path="drafts/test.md",
            sha="abc123" * 7,
        )

        assert result is None

    @patch(
        "backend.infrastructure.versioning.github_revision_service.requests.get"
    )
    def test_fetch_file_at_sha_handles_timeout(
        self, mock_get: Mock, service: GitHubRevisionService
    ) -> None:
        """Fetch file at SHA returns None on request timeout."""
        mock_get.side_effect = requests.exceptions.Timeout()

        result = service.fetch_file_at_sha(
            owner="testowner",
            repo="testrepo",
            path="drafts/test.md",
            sha="abc123" * 7,
        )

        assert result is None

    @patch(
        "backend.infrastructure.versioning.github_revision_service.requests.get"
    )
    def test_fetch_file_at_sha_handles_connection_error(
        self, mock_get: Mock, service: GitHubRevisionService
    ) -> None:
        """Fetch file at SHA returns None on connection error."""
        mock_get.side_effect = requests.exceptions.ConnectionError()

        result = service.fetch_file_at_sha(
            owner="testowner",
            repo="testrepo",
            path="drafts/test.md",
            sha="abc123" * 7,
        )

        assert result is None

    @patch(
        "backend.infrastructure.versioning.github_revision_service.requests.get"
    )
    def test_fetch_file_at_sha_includes_auth_headers(
        self, mock_get: Mock, service: GitHubRevisionService
    ) -> None:
        """Fetch file at SHA includes proper authentication headers."""
        content = "# Test"
        encoded_content = base64.b64encode(content.encode()).decode()
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"content": encoded_content}
        mock_get.return_value = mock_response

        service.fetch_file_at_sha(
            owner="testowner",
            repo="testrepo",
            path="drafts/test.md",
            sha="abc123" * 7,
        )

        args, kwargs = mock_get.call_args
        assert kwargs["headers"]["Authorization"] == "Bearer ghp_testtoken"
        assert kwargs["headers"]["Accept"] == "application/vnd.github.v3+json"


class TestGetHeaders:
    """Test suite for _get_headers private method."""

    def test_get_headers_returns_auth_and_accept_headers(self) -> None:
        """_get_headers returns proper Authorization and Accept headers."""
        service = GitHubRevisionService(
            token="ghp_testtoken", owner="owner", repo="repo"
        )

        headers = service._get_headers()

        assert headers["Authorization"] == "Bearer ghp_testtoken"
        assert headers["Accept"] == "application/vnd.github.v3+json"
        assert len(headers) == 2
