"""Integration tests for health check endpoints.

Tests health monitoring API endpoints for application and dependency health.
"""

from unittest.mock import MagicMock, patch

from requests.exceptions import RequestException


def test_health_endpoint_returns_200(client):
    """GET /api/health should return 200 OK with healthy status."""
    response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json == {"status": "healthy"}


def test_health_endpoint_returns_json(client):
    """GET /api/health should return JSON content type."""
    response = client.get("/api/health")

    assert response.content_type == "application/json"


def test_health_db_success_returns_200(client, dev_settings):
    """GET /api/health/db should return 200 when database is reachable."""
    mock_engine = MagicMock()

    with patch(
        "backend.api.routes.health.get_engine", return_value=mock_engine
    ):
        response = client.get("/api/health/db")

    assert response.status_code == 200
    assert response.json == {"status": "healthy", "database": "connected"}
    mock_engine.connect.assert_called_once()


def test_health_db_failure_returns_503(client):
    """GET /api/health/db should return 503 when database is unreachable."""
    mock_engine = MagicMock()
    mock_engine.connect.return_value.__enter__.side_effect = Exception(
        "Connection refused"
    )

    with patch(
        "backend.api.routes.health.get_engine", return_value=mock_engine
    ):
        response = client.get("/api/health/db")

    assert response.status_code == 503
    assert response.json["status"] == "unhealthy"
    assert "database" in response.json
    assert response.json["database"] == "unreachable"


def test_health_db_returns_json(client, dev_settings):
    """GET /api/health/db should return JSON content type."""
    mock_engine = MagicMock()

    with patch(
        "backend.api.routes.health.get_engine", return_value=mock_engine
    ):
        response = client.get("/api/health/db")

    assert response.content_type == "application/json"


def test_health_github_success_returns_200(client):
    """GET /api/health/github should return 200 when GitHub API is reachable."""
    mock_response = MagicMock()
    mock_response.status_code = 200

    with patch("backend.api.routes.health.requests.get") as mock_get:
        mock_get.return_value = mock_response
        response = client.get("/api/health/github")

    assert response.status_code == 200
    assert response.json == {"status": "healthy", "github": "reachable"}
    mock_get.assert_called_once_with(
        "https://api.github.com/rate_limit", timeout=5
    )


def test_health_github_failure_returns_503(client):
    """GET /api/health/github should return 503 when GitHub API unreachable."""
    with patch("backend.api.routes.health.requests.get") as mock_get:
        mock_get.side_effect = RequestException("Connection timeout")
        response = client.get("/api/health/github")

    assert response.status_code == 503
    assert response.json["status"] == "unhealthy"
    assert "github" in response.json
    assert response.json["github"] == "unreachable"


def test_health_github_non_200_response_returns_503(client):
    """GET /api/health/github returns 503 when GitHub API returns non-200."""
    mock_response = MagicMock()
    mock_response.status_code = 500
    mock_response.raise_for_status.side_effect = RequestException(
        "500 Server Error"
    )

    with patch("backend.api.routes.health.requests.get") as mock_get:
        mock_get.return_value = mock_response
        response = client.get("/api/health/github")

    assert response.status_code == 503
    assert response.json["status"] == "unhealthy"
    assert "github" in response.json
    assert response.json["github"] == "unreachable"


def test_health_github_returns_json(client):
    """GET /api/health/github should return JSON content type."""
    mock_response = MagicMock()
    mock_response.status_code = 200

    with patch("backend.api.routes.health.requests.get") as mock_get:
        mock_get.return_value = mock_response
        response = client.get("/api/health/github")

    assert response.content_type == "application/json"


def test_health_github_uses_timeout(client):
    """GET /api/health/github should use a reasonable timeout."""
    mock_response = MagicMock()
    mock_response.status_code = 200

    with patch("backend.api.routes.health.requests.get") as mock_get:
        mock_get.return_value = mock_response
        client.get("/api/health/github")

    call_kwargs = mock_get.call_args[1]
    assert "timeout" in call_kwargs
    assert call_kwargs["timeout"] <= 10  # Reasonable timeout
