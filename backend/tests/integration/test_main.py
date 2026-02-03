"""Integration tests for SPA routing behavior.

Tests Flask's ability to serve React SPA with proper routing:
- Serve index.html for client-side routes (non-API, non-static)
- Preserve API routes from SPA catch-all
- Serve static files directly from build/static/
- Handle missing index.html gracefully

These tests follow TDD RED phase - they WILL FAIL until implementation exists.
"""

from unittest.mock import MagicMock, patch

from sqlmodel import Session


def test_root_path_serves_index_html(client):
    """GET / should return index.html with 200 status.

    The root path is the primary entry point for the React SPA.
    Flask should serve index.html which loads the React application.
    """
    response = client.get("/")

    assert response.status_code == 200
    assert b"<div id='root'></div>" in response.data
    assert response.content_type == "text/html; charset=utf-8"


def test_spa_route_serves_index_html(client):
    """GET /posts/my-post should return index.html for client-side routing.

    React Router handles routes like /posts/:slug on the client side.
    Flask must serve index.html for these paths (not 404), allowing
    React Router to take over navigation.
    """
    response = client.get("/posts/my-first-post")

    assert response.status_code == 200
    assert b"<div id='root'></div>" in response.data
    assert response.content_type == "text/html; charset=utf-8"


def test_nested_spa_route_serves_index_html(client):
    """GET /admin/settings should return index.html for nested routes.

    Deeply nested client-side routes must also receive index.html,
    not Flask 404 errors. This enables multi-level routing in React.
    """
    response = client.get("/admin/settings")

    assert response.status_code == 200
    assert b"<div id='root'></div>" in response.data
    assert response.content_type == "text/html; charset=utf-8"


def test_api_routes_not_intercepted_by_spa(client):
    """GET /health should return JSON, not index.html.

    API routes (/api/*, /health*) must NOT be caught by the SPA
    catch-all handler. They should return their normal responses.
    """
    response = client.get("/health")

    assert response.status_code == 200
    assert response.content_type == "application/json"
    assert response.json == {"status": "healthy"}


def test_health_db_endpoint_accessible(client, dev_settings):
    """GET /health/db should return JSON response, not SPA HTML.

    Verify health blueprint routes are not intercepted by SPA routing.
    """
    mock_session = MagicMock(spec=Session)
    mock_session.exec.return_value = MagicMock()

    with patch(
        "backend.api.routes.health.get_db", return_value=iter([mock_session])
    ):
        response = client.get("/health/db")

    assert response.status_code == 200
    assert response.content_type == "application/json"
    assert "database" in response.json


def test_health_github_endpoint_accessible(client):
    """GET /health/github should return JSON response, not SPA HTML.

    Verify all health endpoints remain functional with SPA routing.
    """
    mock_response = MagicMock()
    mock_response.status_code = 200

    with patch("backend.api.routes.health.requests.get") as mock_get:
        mock_get.return_value = mock_response
        response = client.get("/health/github")

    assert response.status_code == 200
    assert response.content_type == "application/json"
    assert "github" in response.json


def test_static_files_served_correctly(client):
    """GET /static/js/main.js should be handled by Flask's static serving.

    Static assets (JS, CSS, images) from build/static/ must be served
    by Flask's built-in static file serving, not caught by the SPA handler.
    The Path.exists() mock makes Flask think files exist, so it returns 200.
    """
    response = client.get("/static/js/main.abc123.js")
    assert response.status_code == 200


def test_missing_index_html_returns_503(client):
    """GET / should return 503 when index.html doesn't exist.

    If the React build directory is missing or index.html doesn't exist,
    Flask should return a 503 Service Unavailable error rather than
    crashing or returning an unclear error.
    """
    with patch("pathlib.Path.is_file", return_value=False):
        response = client.get("/")

    assert response.status_code == 503
    assert b"unavailable" in response.data.lower()


def test_api_404_not_caught_by_spa(client):
    """GET /api/nonexistent should return JSON 404, not index.html.

    Non-existent API routes should return proper JSON error responses,
    not fall through to the SPA handler. This prevents confusing errors
    where API clients receive HTML instead of JSON.
    """
    response = client.get("/api/nonexistent-route")

    assert response.status_code == 404
    assert response.content_type == "application/json" or response.is_json
    assert b"<div id='root'></div>" not in response.data


def test_spa_route_with_query_params_serves_index_html(client):
    """GET /search?q=flask should return index.html with query params.

    Client-side routes with query parameters must still receive index.html.
    React Router can then parse and use the query parameters.
    """
    response = client.get("/search?q=flask&page=2")

    assert response.status_code == 200
    assert b"<div id='root'></div>" in response.data
    assert response.content_type == "text/html; charset=utf-8"


def test_spa_route_with_trailing_slash_serves_index_html(client):
    """GET /posts/ should return index.html (trailing slash handling).

    Routes with trailing slashes should also receive index.html for
    consistent client-side routing behavior.
    """
    response = client.get("/posts/")

    assert response.status_code == 200
    assert b"<div id='root'></div>" in response.data
    assert response.content_type == "text/html; charset=utf-8"


def test_favicon_served_from_build_directory(client):
    """GET /favicon.ico should serve from build directory, not index.html.

    Static assets in the build root (favicon, manifest.json, etc.) should
    be served directly from the build directory.
    """
    response = client.get("/favicon.ico")
    assert response.status_code == 200


def test_manifest_json_served_from_build_directory(client):
    """GET /manifest.json should serve from build directory, not index.html.

    PWA manifest and other root-level static files should be accessible.
    """
    response = client.get("/manifest.json")
    assert response.status_code == 200


def test_path_traversal_blocked(client):
    """Path traversal attempts should return 400 Bad Request.

    Security test: Attempts to access files outside build directory
    using ".." should be blocked.
    """
    response = client.get("/../etc/passwd")

    assert response.status_code == 400
    assert response.json == {"error": "Invalid path"}


def test_path_traversal_in_middle_blocked(client):
    """Path traversal in middle of path should return 400.

    Security test: Even if traversal is in the middle of a valid-looking
    path, it should still be blocked.
    """
    response = client.get("/posts/../../../secrets.txt")

    assert response.status_code == 400
    assert response.json == {"error": "Invalid path"}


def test_url_encoded_path_traversal_blocked(client):
    """URL-encoded path traversal should be decoded and blocked.

    Security test: Attackers may URL-encode ".." as %2e%2e to bypass
    naive checks. Double decoding ensures detection.
    """
    response = client.get("/%2e%2e/etc/passwd")

    assert response.status_code == 400
    assert response.json == {"error": "Invalid path"}


def test_backslash_path_traversal_blocked(client):
    r"""Backslash path traversal should be blocked.

    Security test: Windows-style path traversal using backslashes
    should also be blocked.
    """
    response = client.get("/..\\secrets.txt")

    assert response.status_code == 400
    assert response.json == {"error": "Invalid path"}


def test_file_access_exception_handling(client):
    """OSError during file access should return 503 Service Unavailable.

    When file.is_file() raises OSError (permissions, I/O error),
    the SPA handler should return a 503 error instead of crashing.
    """
    with patch(
        "pathlib.Path.is_file", side_effect=OSError("Permission denied")
    ):
        response = client.get("/some-path")

    assert response.status_code == 503
    assert b"unavailable" in response.data.lower()
