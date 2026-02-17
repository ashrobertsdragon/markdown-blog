"""Integration tests for SPA routing behavior.

Tests Flask's ability to serve React SPA with proper routing:
- Serve index.html for client-side routes (non-API, non-static)
- Preserve API routes from SPA catch-all
- Serve static files directly from build/static/
- Handle missing index.html gracefully

These tests follow TDD RED phase - they WILL FAIL until implementation exists.
"""

from unittest.mock import MagicMock, patch


def test_root_path_serves_index_html(client):
    """GET / should return index.html with 200 status."""
    with client.get("/") as response:
        assert response.status_code == 200
        assert b"<div id='root'></div>" in response.data
        assert response.content_type == "text/html; charset=utf-8"


def test_spa_route_serves_index_html(client):
    """GET /posts/my-post should return index.html for client-side routing."""
    with client.get("/posts/my-first-post") as response:
        assert response.status_code == 200
        assert b"<div id='root'></div>" in response.data
        assert response.content_type == "text/html; charset=utf-8"


def test_nested_spa_route_serves_index_html(client):
    """GET /admin/settings should return index.html for nested routes."""
    with client.get("/admin/settings") as response:
        assert response.status_code == 200
        assert b"<div id='root'></div>" in response.data
        assert response.content_type == "text/html; charset=utf-8"


def test_api_routes_not_intercepted_by_spa(client):
    """GET /api/health should return JSON, not index.html."""
    with client.get("/api/health") as response:
        assert response.status_code == 200
        assert response.content_type == "application/json"
        assert response.json == {"status": "healthy"}


def test_health_db_endpoint_accessible(client, dev_settings):
    """GET /api/health/db should return JSON response, not SPA HTML."""
    mock_engine = MagicMock()

    with patch(
        "backend.api.routes.health.get_engine", return_value=mock_engine
    ):
        with client.get("/api/health/db") as response:
            assert response.status_code == 200
            assert response.content_type == "application/json"
            assert "database" in response.json


def test_health_github_endpoint_accessible(client):
    """GET /api/health/github should return JSON response, not SPA HTML."""
    mock_response = MagicMock()
    mock_response.status_code = 200

    with patch("backend.api.routes.health.requests.get") as mock_get:
        mock_get.return_value = mock_response
        with client.get("/api/health/github") as response:
            assert response.status_code == 200
            assert response.content_type == "application/json"
            assert "github" in response.json


def test_static_files_served_correctly(client):
    """GET /static/js/main.js should be handled by Flask's static serving."""
    with client.get("/static/js/main.abc123.js") as response:
        assert response.status_code == 200


def test_missing_index_html_returns_503(client):
    """GET / should return 503 when index.html doesn't exist."""
    with patch("pathlib.Path.is_file", return_value=False):
        with client.get("/") as response:
            assert response.status_code == 503
            assert b"unavailable" in response.data.lower()


def test_api_404_not_caught_by_spa(client):
    """GET /api/nonexistent should return JSON 404, not index.html."""
    with client.get("/api/nonexistent-route") as response:
        assert response.status_code == 404
        assert response.content_type == "application/json" or response.is_json
        assert b"<div id='root'></div>" not in response.data


def test_spa_route_with_query_params_serves_index_html(client):
    """GET /search?q=flask should return index.html with query params."""
    with client.get("/search?q=flask&page=2") as response:
        assert response.status_code == 200
        assert b"<div id='root'></div>" in response.data
        assert response.content_type == "text/html; charset=utf-8"


def test_spa_route_with_trailing_slash_serves_index_html(client):
    """GET /posts/ should return index.html (trailing slash handling)."""
    with client.get("/posts/") as response:
        assert response.status_code == 200
        assert b"<div id='root'></div>" in response.data
        assert response.content_type == "text/html; charset=utf-8"


def test_favicon_served_from_build_directory(client):
    """GET /favicon.ico should serve from build directory, not index.html."""
    with client.get("/favicon.ico") as response:
        assert response.status_code == 200


def test_manifest_json_served_from_build_directory(client):
    """GET /manifest.json should serve from build directory, not index.html."""
    with client.get("/manifest.json") as response:
        assert response.status_code == 200


def test_path_traversal_blocked(client):
    """Path traversal attempts should return 400 Bad Request."""
    with client.get("/../etc/passwd") as response:
        assert response.status_code == 400
        assert response.json == {"error": "Invalid path"}


def test_path_traversal_in_middle_blocked(client):
    """Path traversal in middle of path should return 400."""
    with client.get("/posts/../../../secrets.txt") as response:
        assert response.status_code == 400
        assert response.json == {"error": "Invalid path"}


def test_url_encoded_path_traversal_blocked(client):
    """URL-encoded path traversal should be decoded and blocked."""
    with client.get("/%2e%2e/etc/passwd") as response:
        assert response.status_code == 400
        assert response.json == {"error": "Invalid path"}


def test_backslash_path_traversal_blocked(client):
    r"""Backslash path traversal should be blocked."""
    with client.get("/..\\secrets.txt") as response:
        assert response.status_code == 400
        assert response.json == {"error": "Invalid path"}


def test_file_access_exception_handling(client):
    """OSError during file access should return 503 Service Unavailable."""
    with patch(
        "pathlib.Path.is_file", side_effect=OSError("Permission denied")
    ):
        with client.get("/some-path") as response:
            assert response.status_code == 503
            assert b"unavailable" in response.data.lower()
