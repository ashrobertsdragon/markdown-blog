from unittest.mock import Mock, patch

import pytest
import requests

from backend.infrastructure.versioning.github_sync_service import (
    GitHubSyncService,
)


@pytest.fixture
def github_token() -> str:
    """Fixture providing test GitHub personal access token."""
    return "ghp_test123456789abcdef"


@pytest.fixture
def repo_owner() -> str:
    """Fixture providing test GitHub repository owner."""
    return "testuser"


@pytest.fixture
def repo_name() -> str:
    """Fixture providing test GitHub repository name."""
    return "test-repo"


@pytest.fixture
def sync_service(
    github_token: str, repo_owner: str, repo_name: str
) -> GitHubSyncService:
    """Fixture providing configured GitHubSyncService instance."""
    return GitHubSyncService(
        token=github_token, owner=repo_owner, repo=repo_name
    )


@pytest.fixture
def mock_github_response() -> Mock:
    """Fixture providing mock GitHub API response."""
    response = Mock()
    response.status_code = 200
    response.json.return_value = {
        "commit": {"sha": "abc123def456"},
        "content": {"sha": "file789xyz"},
    }
    return response


def test_github_sync_service_initializes_with_valid_params(
    github_token: str, repo_owner: str, repo_name: str
) -> None:
    service = GitHubSyncService(
        token=github_token, owner=repo_owner, repo=repo_name
    )
    assert service is not None


def test_github_sync_service_raises_valueerror_for_empty_token(
    repo_owner: str, repo_name: str
) -> None:
    with pytest.raises(ValueError, match="GitHub token cannot be empty"):
        GitHubSyncService(token="", owner=repo_owner, repo=repo_name)


def test_github_sync_service_raises_valueerror_for_empty_owner(
    github_token: str, repo_name: str
) -> None:
    with pytest.raises(ValueError, match="Repository owner cannot be empty"):
        GitHubSyncService(token=github_token, owner="", repo=repo_name)


def test_github_sync_service_raises_valueerror_for_empty_repo(
    github_token: str, repo_owner: str
) -> None:
    with pytest.raises(ValueError, match="Repository name cannot be empty"):
        GitHubSyncService(token=github_token, owner=repo_owner, repo="")


@patch("backend.infrastructure.versioning.github_sync_service.requests.get")
@patch("backend.infrastructure.versioning.github_sync_service.requests.put")
def test_commit_file_creates_new_file_successfully(
    mock_put: Mock, mock_get: Mock, sync_service: GitHubSyncService
) -> None:
    """Test committing a new file that doesn't exist in the repository."""
    mock_get.return_value.status_code = 404
    mock_put.return_value.status_code = 201
    mock_put.return_value.json.return_value = {"commit": {"sha": "abc123"}}

    result = sync_service.commit_file(
        path="drafts/new-post.md",
        content="# New Post",
        message="Create new post",
    )

    assert result == "abc123"
    mock_get.assert_called_once()
    mock_put.assert_called_once()


@patch("backend.infrastructure.versioning.github_sync_service.requests.get")
@patch("backend.infrastructure.versioning.github_sync_service.requests.put")
def test_commit_file_updates_existing_file_successfully(
    mock_put: Mock, mock_get: Mock, sync_service: GitHubSyncService
) -> None:
    """Test updating an existing file with SHA tracking."""
    mock_get.return_value.status_code = 200
    mock_get.return_value.json.return_value = {"sha": "oldsha789"}
    mock_put.return_value.status_code = 200
    mock_put.return_value.json.return_value = {"commit": {"sha": "newsha123"}}

    result = sync_service.commit_file(
        path="drafts/existing-post.md",
        content="# Updated Post",
        message="Update existing post",
    )

    assert result == "newsha123"
    assert mock_get.call_count == 1
    assert mock_put.call_count == 1


@patch("backend.infrastructure.versioning.github_sync_service.requests.get")
@patch("backend.infrastructure.versioning.github_sync_service.requests.put")
def test_commit_file_returns_commit_sha_from_response(
    mock_put: Mock, mock_get: Mock, sync_service: GitHubSyncService
) -> None:
    """Test that commit_file extracts and returns the commit SHA."""
    mock_get.return_value.status_code = 404
    mock_put.return_value.status_code = 201
    expected_sha = "commit567890abcdef"
    mock_put.return_value.json.return_value = {"commit": {"sha": expected_sha}}

    result = sync_service.commit_file(
        path="drafts/test.md", content="content", message="test commit"
    )

    assert result == expected_sha


@patch("backend.infrastructure.versioning.github_sync_service.requests.get")
@patch("backend.infrastructure.versioning.github_sync_service.requests.put")
@patch("backend.infrastructure.versioning.github_sync_service.time.sleep")
def test_commit_file_retries_on_rate_limit_with_exponential_backoff(
    mock_sleep: Mock,
    mock_put: Mock,
    mock_get: Mock,
    sync_service: GitHubSyncService,
) -> None:
    """Test retry logic with exponential backoff on HTTP 429 rate limit."""
    mock_get.return_value.status_code = 404
    mock_put.side_effect = [
        Mock(status_code=429),
        Mock(status_code=429),
        Mock(status_code=201, json=lambda: {"commit": {"sha": "success123"}}),
    ]

    result = sync_service.commit_file(
        path="drafts/post.md", content="content", message="commit"
    )

    assert result == "success123"
    assert mock_put.call_count == 3
    assert mock_sleep.call_count == 2
    mock_sleep.assert_any_call(1)
    mock_sleep.assert_any_call(2)


@patch("backend.infrastructure.versioning.github_sync_service.requests.get")
@patch("backend.infrastructure.versioning.github_sync_service.requests.put")
@patch("backend.infrastructure.versioning.github_sync_service.time.sleep")
def test_commit_file_succeeds_on_second_retry(
    mock_sleep: Mock,
    mock_put: Mock,
    mock_get: Mock,
    sync_service: GitHubSyncService,
) -> None:
    """Test successful commit after one retry attempt."""
    mock_get.return_value.status_code = 404
    mock_put.side_effect = [
        Mock(status_code=429),
        Mock(status_code=201, json=lambda: {"commit": {"sha": "retry456"}}),
    ]

    result = sync_service.commit_file(
        path="drafts/post.md", content="content", message="commit"
    )

    assert result == "retry456"
    assert mock_put.call_count == 2
    assert mock_sleep.call_count == 1


@patch("backend.infrastructure.versioning.github_sync_service.requests.get")
@patch("backend.infrastructure.versioning.github_sync_service.requests.put")
@patch("backend.infrastructure.versioning.github_sync_service.time.sleep")
def test_commit_file_exhausts_retries_and_returns_none(
    mock_sleep: Mock,
    mock_put: Mock,
    mock_get: Mock,
    sync_service: GitHubSyncService,
) -> None:
    """Test that after 3 failed retries, commit_file returns None."""
    mock_get.return_value.status_code = 404
    mock_put.return_value = Mock(status_code=429)

    result = sync_service.commit_file(
        path="drafts/post.md", content="content", message="commit"
    )

    assert result is None
    assert mock_put.call_count == 3
    assert mock_sleep.call_count == 3


@patch("backend.infrastructure.versioning.github_sync_service.requests.get")
@patch("backend.infrastructure.versioning.github_sync_service.requests.put")
@patch("backend.infrastructure.versioning.github_sync_service.time.sleep")
def test_commit_file_logs_each_retry_attempt(
    mock_sleep: Mock,
    mock_put: Mock,
    mock_get: Mock,
    sync_service: GitHubSyncService,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test that each retry attempt is logged for debugging."""
    mock_get.return_value.status_code = 404
    mock_put.return_value = Mock(status_code=429)

    sync_service.commit_file(
        path="drafts/post.md", content="content", message="commit"
    )

    assert "Retry attempt 1" in caplog.text
    assert "Retry attempt 2" in caplog.text
    assert "Retry attempt 3" in caplog.text


@patch("backend.infrastructure.versioning.github_sync_service.requests.get")
@patch("backend.infrastructure.versioning.github_sync_service.requests.put")
def test_commit_file_returns_none_on_http_401_unauthorized(
    mock_put: Mock,
    mock_get: Mock,
    sync_service: GitHubSyncService,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test error handling for authentication failure."""
    mock_get.return_value.status_code = 404
    mock_put.return_value.status_code = 401

    result = sync_service.commit_file(
        path="drafts/post.md", content="content", message="commit"
    )

    assert result is None
    assert "401" in caplog.text or "Unauthorized" in caplog.text


@patch("backend.infrastructure.versioning.github_sync_service.requests.get")
@patch("backend.infrastructure.versioning.github_sync_service.requests.put")
def test_commit_file_returns_none_on_http_403_forbidden(
    mock_put: Mock,
    mock_get: Mock,
    sync_service: GitHubSyncService,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test error handling for permission denied."""
    mock_get.return_value.status_code = 404
    mock_put.return_value.status_code = 403

    result = sync_service.commit_file(
        path="drafts/post.md", content="content", message="commit"
    )

    assert result is None
    assert "403" in caplog.text or "Forbidden" in caplog.text


@patch("backend.infrastructure.versioning.github_sync_service.requests.get")
@patch("backend.infrastructure.versioning.github_sync_service.requests.put")
def test_commit_file_returns_none_on_http_404_not_found(
    mock_put: Mock,
    mock_get: Mock,
    sync_service: GitHubSyncService,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test error handling for repository not found."""
    mock_get.return_value.status_code = 404
    mock_put.return_value.status_code = 404

    result = sync_service.commit_file(
        path="drafts/post.md", content="content", message="commit"
    )

    assert result is None
    assert "404" in caplog.text or "Not Found" in caplog.text


@patch("backend.infrastructure.versioning.github_sync_service.requests.get")
@patch("backend.infrastructure.versioning.github_sync_service.requests.put")
def test_commit_file_returns_none_on_http_500_server_error(
    mock_put: Mock,
    mock_get: Mock,
    sync_service: GitHubSyncService,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test error handling for GitHub server errors."""
    mock_get.return_value.status_code = 404
    mock_put.return_value.status_code = 500

    result = sync_service.commit_file(
        path="drafts/post.md", content="content", message="commit"
    )

    assert result is None
    assert "500" in caplog.text or "Server Error" in caplog.text


@patch("backend.infrastructure.versioning.github_sync_service.requests.get")
@patch("backend.infrastructure.versioning.github_sync_service.requests.put")
def test_commit_file_returns_none_on_network_timeout(
    mock_put: Mock,
    mock_get: Mock,
    sync_service: GitHubSyncService,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test error handling for network timeout exceptions."""
    mock_get.return_value.status_code = 404
    mock_put.side_effect = requests.exceptions.Timeout("Connection timeout")

    result = sync_service.commit_file(
        path="drafts/post.md", content="content", message="commit"
    )

    assert result is None
    assert "timeout" in caplog.text.lower() or "Timeout" in caplog.text


@patch("backend.infrastructure.versioning.github_sync_service.requests.get")
@patch("backend.infrastructure.versioning.github_sync_service.requests.put")
def test_commit_file_returns_none_on_connection_error(
    mock_put: Mock,
    mock_get: Mock,
    sync_service: GitHubSyncService,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test error handling for network connection failures."""
    mock_get.return_value.status_code = 404
    mock_put.side_effect = requests.exceptions.ConnectionError(
        "Connection refused"
    )

    result = sync_service.commit_file(
        path="drafts/post.md", content="content", message="commit"
    )

    assert result is None
    assert "connection" in caplog.text.lower() or "Connection" in caplog.text


@patch("backend.infrastructure.versioning.github_sync_service.requests.get")
@patch("backend.infrastructure.versioning.github_sync_service.requests.delete")
def test_delete_file_removes_file_successfully(
    mock_delete: Mock, mock_get: Mock, sync_service: GitHubSyncService
) -> None:
    """Test successful file deletion from repository."""
    mock_get.return_value.status_code = 200
    mock_get.return_value.json.return_value = {"sha": "filesha123"}
    mock_delete.return_value.status_code = 200

    result = sync_service.delete_file(
        path="drafts/old-post.md", message="Delete old post"
    )

    assert result is True
    mock_get.assert_called_once()
    mock_delete.assert_called_once()


@patch("backend.infrastructure.versioning.github_sync_service.requests.get")
@patch("backend.infrastructure.versioning.github_sync_service.requests.delete")
def test_delete_file_returns_false_when_file_not_found(
    mock_delete: Mock, mock_get: Mock, sync_service: GitHubSyncService
) -> None:
    """Test delete_file returns False when file doesn't exist."""
    mock_get.return_value.status_code = 404

    result = sync_service.delete_file(
        path="drafts/nonexistent.md", message="Delete nonexistent"
    )

    assert result is False
    mock_get.assert_called_once()
    mock_delete.assert_not_called()


@patch("backend.infrastructure.versioning.github_sync_service.requests.get")
@patch("backend.infrastructure.versioning.github_sync_service.requests.delete")
def test_delete_file_returns_false_on_api_error(
    mock_delete: Mock,
    mock_get: Mock,
    sync_service: GitHubSyncService,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test delete_file returns False and logs error on API failure."""
    mock_get.return_value.status_code = 200
    mock_get.return_value.json.return_value = {"sha": "filesha123"}
    mock_delete.return_value.status_code = 500

    result = sync_service.delete_file(
        path="drafts/post.md", message="Delete post"
    )

    assert result is False
    assert "500" in caplog.text or "error" in caplog.text.lower()


@patch("backend.infrastructure.versioning.github_sync_service.requests.get")
@patch("backend.infrastructure.versioning.github_sync_service.requests.put")
def test_commit_file_returns_none_on_request_exception(
    mock_put: Mock,
    mock_get: Mock,
    sync_service: GitHubSyncService,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test error handling for generic request exceptions."""
    mock_get.return_value.status_code = 404
    mock_put.side_effect = requests.exceptions.RequestException(
        "Generic request error"
    )

    result = sync_service.commit_file(
        path="drafts/post.md", content="content", message="commit"
    )

    assert result is None
    assert "request error" in caplog.text.lower()


@patch("backend.infrastructure.versioning.github_sync_service.requests.get")
@patch("backend.infrastructure.versioning.github_sync_service.requests.delete")
def test_delete_file_returns_false_on_timeout(
    mock_delete: Mock,
    mock_get: Mock,
    sync_service: GitHubSyncService,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test error handling for timeout in delete operation."""
    mock_get.return_value.status_code = 200
    mock_get.return_value.json.return_value = {"sha": "filesha123"}
    mock_delete.side_effect = requests.exceptions.Timeout("Delete timeout")

    result = sync_service.delete_file(
        path="drafts/post.md", message="Delete post"
    )

    assert result is False
    assert "timeout" in caplog.text.lower()


@patch("backend.infrastructure.versioning.github_sync_service.requests.get")
@patch("backend.infrastructure.versioning.github_sync_service.requests.delete")
def test_delete_file_returns_false_on_connection_error(
    mock_delete: Mock,
    mock_get: Mock,
    sync_service: GitHubSyncService,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test error handling for connection error in delete operation."""
    mock_get.return_value.status_code = 200
    mock_get.return_value.json.return_value = {"sha": "filesha123"}
    mock_delete.side_effect = requests.exceptions.ConnectionError(
        "Connection refused"
    )

    result = sync_service.delete_file(
        path="drafts/post.md", message="Delete post"
    )

    assert result is False
    assert "connection" in caplog.text.lower()


@patch("backend.infrastructure.versioning.github_sync_service.requests.get")
def test_get_file_sha_returns_none_on_key_error(
    mock_get: Mock,
    sync_service: GitHubSyncService,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test error handling for missing SHA key in response."""
    mock_get.return_value.status_code = 200
    mock_get.return_value.json.return_value = {"no_sha_key": "value"}

    result = sync_service._get_file_sha("drafts/post.md")

    assert result is None
    assert "parsing error" in caplog.text.lower() or "KeyError" in caplog.text
