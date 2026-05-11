"""Integration tests for admin blueprint registration in the Flask app.

Verifies that the admin blueprint (admin_bp) is correctly registered in
create_app(), that all /api/admin/* routes are reachable, that every route
enforces authentication and admin-role authorisation, and that the response
shapes satisfy requirements 8.1–8.6.

These tests are in the RED phase: they verify behaviour against a fully-wired
Flask application using mocked infrastructure dependencies.
"""

from datetime import UTC, datetime
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from backend.application.queries.get_system_health_query import SystemHealth
from backend.application.queries.get_user_activity_query import UserActivity
from backend.domain.aggregates.post import Post
from backend.domain.aggregates.user import User
from backend.domain.value_objects.role import Role
from backend.exceptions import NotFoundError
from backend.infrastructure.monitoring.error_logger import (
    ErrorEntry,
    ErrorLogger,
)
from backend.main import create_app


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _clear_error_logger() -> Any:
    """Isolate ErrorLogger state between tests."""
    ErrorLogger.clear()
    yield
    ErrorLogger.clear()


@pytest.fixture
def admin_user() -> User:
    """Admin user aggregate used to simulate a privileged caller."""
    return User(
        id=1,
        clerk_user_id="clerk_admin_001",
        email="admin@example.com",
        role=Role.ADMIN,
        created_at=datetime(2024, 1, 1, tzinfo=UTC),
    )


@pytest.fixture
def regular_user() -> User:
    """Authenticated non-admin user aggregate."""
    return User(
        id=2,
        clerk_user_id="clerk_user_002",
        email="user@example.com",
        role=Role.AUTHENTICATED,
        created_at=datetime(2024, 2, 1, tzinfo=UTC),
    )


@pytest.fixture
def admin_jwt_payload() -> dict[str, Any]:
    """Minimal decoded JWT payload for an admin caller."""
    return {
        "sub": "clerk_admin_001",
        "email": "admin@example.com",
        "exp": 9999999999,
    }


@pytest.fixture
def regular_jwt_payload() -> dict[str, Any]:
    """Minimal decoded JWT payload for a non-admin caller."""
    return {
        "sub": "clerk_user_002",
        "email": "user@example.com",
        "exp": 9999999999,
    }


@pytest.fixture
def published_post() -> Post:
    """A published Post aggregate with a known id."""
    post = Post.create_draft(
        slug="test-article", title="Test Article", author_id=1
    )
    post.publish("<p>content</p>")
    post.id = 42
    return post


@pytest.fixture
def draft_post() -> Post:
    """An unpublished (draft) Post aggregate."""
    post = Post.create_draft(
        slug="draft-article", title="Draft Article", author_id=1
    )
    post.id = 99
    return post


# ---------------------------------------------------------------------------
# Helper: auth patch context manager factory
# ---------------------------------------------------------------------------


def _auth_patches(
    jwt_payload: dict[str, Any],
    user: User,
) -> tuple[Any, Any]:
    """Return (mock_clerk, mock_user_repo) preconfigured for the given identity."""
    mock_clerk = MagicMock()
    mock_clerk.verify_token.return_value = jwt_payload

    mock_user_repo = MagicMock()
    mock_user_repo.find_by_clerk_user_id.return_value = user

    return mock_clerk, mock_user_repo


# ---------------------------------------------------------------------------
# Section 1 – Blueprint registration
# ---------------------------------------------------------------------------


def test_admin_blueprint_is_registered_in_app(client: Any) -> None:
    """The Flask app exposes an 'admin' blueprint after create_app()."""
    app = create_app()
    assert "admin" in app.blueprints


def test_admin_blueprint_url_prefix(client: Any) -> None:
    """All registered admin URL rules begin with /api/admin."""
    app = create_app()
    admin_rules = [
        str(rule) for rule in app.url_map.iter_rules() if "admin" in str(rule)
    ]
    assert any("/api/admin" in rule for rule in admin_rules)


def test_unpublish_route_registered(client: Any) -> None:
    """POST /api/admin/posts/<id>/unpublish is a known URL rule."""
    app = create_app()
    rules = [str(rule) for rule in app.url_map.iter_rules()]
    assert any(
        "/api/admin/posts/" in rule and "unpublish" in rule for rule in rules
    )


def test_user_activity_route_registered(client: Any) -> None:
    """GET /api/admin/users/<id>/activity is a known URL rule."""
    app = create_app()
    rules = [str(rule) for rule in app.url_map.iter_rules()]
    assert any(
        "/api/admin/users/" in rule and "activity" in rule for rule in rules
    )


def test_system_health_route_registered(client: Any) -> None:
    """GET /api/admin/system/health is a known URL rule."""
    app = create_app()
    rules = [str(rule) for rule in app.url_map.iter_rules()]
    assert "/api/admin/system/health" in rules


def test_system_errors_route_registered(client: Any) -> None:
    """GET /api/admin/system/errors is a known URL rule."""
    app = create_app()
    rules = [str(rule) for rule in app.url_map.iter_rules()]
    assert "/api/admin/system/errors" in rules


# ---------------------------------------------------------------------------
# Section 2 – Authentication enforcement (Req 8.6)
# ---------------------------------------------------------------------------


def test_unpublish_requires_bearer_token(client: Any) -> None:
    """POST /api/admin/posts/1/unpublish returns 401 without Authorization header."""
    response = client.post("/api/admin/posts/1/unpublish")
    assert response.status_code == 401
    assert "error" in response.json


def test_user_activity_requires_bearer_token(client: Any) -> None:
    """GET /api/admin/users/1/activity returns 401 without Authorization header."""
    response = client.get("/api/admin/users/1/activity")
    assert response.status_code == 401
    assert "error" in response.json


def test_system_health_requires_bearer_token(client: Any) -> None:
    """GET /api/admin/system/health returns 401 without Authorization header."""
    response = client.get("/api/admin/system/health")
    assert response.status_code == 401
    assert "error" in response.json


def test_system_errors_requires_bearer_token(client: Any) -> None:
    """GET /api/admin/system/errors returns 401 without Authorization header."""
    response = client.get("/api/admin/system/errors")
    assert response.status_code == 401
    assert "error" in response.json


# ---------------------------------------------------------------------------
# Section 3 – Admin-role enforcement (Req 8.6)
# ---------------------------------------------------------------------------


def test_unpublish_rejects_non_admin_user(
    client: Any,
    regular_user: User,
    regular_jwt_payload: dict[str, Any],
) -> None:
    """POST /api/admin/posts/1/unpublish returns 403 for authenticated non-admins."""
    mock_clerk, mock_user_repo = _auth_patches(
        regular_jwt_payload, regular_user
    )
    with (
        patch(
            "backend.api.middleware.auth_middleware._get_clerk_adapter",
            return_value=mock_clerk,
        ),
        patch(
            "backend.api.middleware.auth_middleware._get_user_repository",
            return_value=mock_user_repo,
        ),
    ):
        response = client.post(
            "/api/admin/posts/1/unpublish",
            headers={"Authorization": "Bearer non_admin_token"},
        )

    assert response.status_code == 403
    assert "error" in response.json


def test_user_activity_rejects_non_admin_user(
    client: Any,
    regular_user: User,
    regular_jwt_payload: dict[str, Any],
) -> None:
    """GET /api/admin/users/1/activity returns 403 for authenticated non-admins."""
    mock_clerk, mock_user_repo = _auth_patches(
        regular_jwt_payload, regular_user
    )
    with (
        patch(
            "backend.api.middleware.auth_middleware._get_clerk_adapter",
            return_value=mock_clerk,
        ),
        patch(
            "backend.api.middleware.auth_middleware._get_user_repository",
            return_value=mock_user_repo,
        ),
    ):
        response = client.get(
            "/api/admin/users/1/activity",
            headers={"Authorization": "Bearer non_admin_token"},
        )

    assert response.status_code == 403
    assert "error" in response.json


def test_system_health_rejects_non_admin_user(
    client: Any,
    regular_user: User,
    regular_jwt_payload: dict[str, Any],
) -> None:
    """GET /api/admin/system/health returns 403 for authenticated non-admins."""
    mock_clerk, mock_user_repo = _auth_patches(
        regular_jwt_payload, regular_user
    )
    with (
        patch(
            "backend.api.middleware.auth_middleware._get_clerk_adapter",
            return_value=mock_clerk,
        ),
        patch(
            "backend.api.middleware.auth_middleware._get_user_repository",
            return_value=mock_user_repo,
        ),
    ):
        response = client.get(
            "/api/admin/system/health",
            headers={"Authorization": "Bearer non_admin_token"},
        )

    assert response.status_code == 403


def test_system_errors_rejects_non_admin_user(
    client: Any,
    regular_user: User,
    regular_jwt_payload: dict[str, Any],
) -> None:
    """GET /api/admin/system/errors returns 403 for authenticated non-admins."""
    mock_clerk, mock_user_repo = _auth_patches(
        regular_jwt_payload, regular_user
    )
    with (
        patch(
            "backend.api.middleware.auth_middleware._get_clerk_adapter",
            return_value=mock_clerk,
        ),
        patch(
            "backend.api.middleware.auth_middleware._get_user_repository",
            return_value=mock_user_repo,
        ),
    ):
        response = client.get(
            "/api/admin/system/errors",
            headers={"Authorization": "Bearer non_admin_token"},
        )

    assert response.status_code == 403


# ---------------------------------------------------------------------------
# Section 4 – System health endpoint (Req 8.4)
# ---------------------------------------------------------------------------


def test_system_health_returns_200_with_required_fields(
    client: Any,
    admin_user: User,
    admin_jwt_payload: dict[str, Any],
) -> None:
    """GET /api/admin/system/health returns 200 with status, api_status, database_status, uptime."""
    mock_clerk, mock_user_repo = _auth_patches(admin_jwt_payload, admin_user)

    health_result = SystemHealth(
        api_status="Healthy",
        database_status="Healthy",
        uptime=7200,
    )
    mock_handler = MagicMock()
    mock_handler.handle.return_value = health_result

    with (
        patch(
            "backend.api.middleware.auth_middleware._get_clerk_adapter",
            return_value=mock_clerk,
        ),
        patch(
            "backend.api.middleware.auth_middleware._get_user_repository",
            return_value=mock_user_repo,
        ),
        patch(
            "backend.api.routes.admin._get_system_health_handler",
            return_value=mock_handler,
        ),
    ):
        response = client.get(
            "/api/admin/system/health",
            headers={"Authorization": "Bearer admin_token"},
        )

    assert response.status_code == 200
    body = response.json
    assert "api_status" in body
    assert "database_status" in body
    assert "uptime" in body
    assert body["api_status"] == "Healthy"
    assert body["database_status"] == "Healthy"
    assert isinstance(body["uptime"], int)


def test_system_health_api_status_is_string(
    client: Any,
    admin_user: User,
    admin_jwt_payload: dict[str, Any],
) -> None:
    """api_status field in health response is a non-empty string."""
    mock_clerk, mock_user_repo = _auth_patches(admin_jwt_payload, admin_user)
    mock_handler = MagicMock()
    mock_handler.handle.return_value = SystemHealth(
        api_status="Healthy", database_status="Degraded", uptime=100
    )

    with (
        patch(
            "backend.api.middleware.auth_middleware._get_clerk_adapter",
            return_value=mock_clerk,
        ),
        patch(
            "backend.api.middleware.auth_middleware._get_user_repository",
            return_value=mock_user_repo,
        ),
        patch(
            "backend.api.routes.admin._get_system_health_handler",
            return_value=mock_handler,
        ),
    ):
        response = client.get(
            "/api/admin/system/health",
            headers={"Authorization": "Bearer admin_token"},
        )

    assert isinstance(response.json["api_status"], str)
    assert len(response.json["api_status"]) > 0


# ---------------------------------------------------------------------------
# Section 5 – Error logs endpoint (Req 8.5)
# ---------------------------------------------------------------------------


def test_system_errors_returns_200_with_errors_list(
    client: Any,
    admin_user: User,
    admin_jwt_payload: dict[str, Any],
) -> None:
    """GET /api/admin/system/errors returns 200 with an 'errors' list."""
    mock_clerk, mock_user_repo = _auth_patches(admin_jwt_payload, admin_user)

    with (
        patch(
            "backend.api.middleware.auth_middleware._get_clerk_adapter",
            return_value=mock_clerk,
        ),
        patch(
            "backend.api.middleware.auth_middleware._get_user_repository",
            return_value=mock_user_repo,
        ),
        patch(
            "backend.api.routes.admin.ErrorLogger.get_recent_errors",
            return_value=[],
        ),
    ):
        response = client.get(
            "/api/admin/system/errors",
            headers={"Authorization": "Bearer admin_token"},
        )

    assert response.status_code == 200
    body = response.json
    assert "errors" in body
    assert isinstance(body["errors"], list)


def test_system_errors_entry_shape_matches_schema(
    client: Any,
    admin_user: User,
    admin_jwt_payload: dict[str, Any],
) -> None:
    """Each error entry contains timestamp, message, stack_trace, and endpoint."""
    mock_clerk, mock_user_repo = _auth_patches(admin_jwt_payload, admin_user)

    sample_entry = ErrorEntry(
        timestamp=datetime(2024, 6, 1, 12, 0, 0, tzinfo=UTC),
        message="Something broke",
        stack_trace="Traceback (most recent call last): ...",
        endpoint="/api/posts",
    )

    with (
        patch(
            "backend.api.middleware.auth_middleware._get_clerk_adapter",
            return_value=mock_clerk,
        ),
        patch(
            "backend.api.middleware.auth_middleware._get_user_repository",
            return_value=mock_user_repo,
        ),
        patch(
            "backend.api.routes.admin.ErrorLogger.get_recent_errors",
            return_value=[sample_entry],
        ),
    ):
        response = client.get(
            "/api/admin/system/errors",
            headers={"Authorization": "Bearer admin_token"},
        )

    assert response.status_code == 200
    errors = response.json["errors"]
    assert len(errors) == 1
    entry = errors[0]
    assert "timestamp" in entry
    assert "message" in entry
    assert "stack_trace" in entry
    assert "endpoint" in entry
    assert entry["message"] == "Something broke"
    assert entry["endpoint"] == "/api/posts"


def test_system_errors_limit_query_param_accepted(
    client: Any,
    admin_user: User,
    admin_jwt_payload: dict[str, Any],
) -> None:
    """GET /api/admin/system/errors?limit=10 is accepted and returns 200."""
    mock_clerk, mock_user_repo = _auth_patches(admin_jwt_payload, admin_user)

    with (
        patch(
            "backend.api.middleware.auth_middleware._get_clerk_adapter",
            return_value=mock_clerk,
        ),
        patch(
            "backend.api.middleware.auth_middleware._get_user_repository",
            return_value=mock_user_repo,
        ),
        patch(
            "backend.api.routes.admin.ErrorLogger.get_recent_errors",
            return_value=[],
        ) as mock_get_recent,
    ):
        response = client.get(
            "/api/admin/system/errors?limit=10",
            headers={"Authorization": "Bearer admin_token"},
        )

    assert response.status_code == 200
    mock_get_recent.assert_called_once_with(limit=10)


# ---------------------------------------------------------------------------
# Section 6 – Unpublish post endpoint (Req 8.1)
# ---------------------------------------------------------------------------


def test_unpublish_post_admin_success(
    client: Any,
    admin_user: User,
    admin_jwt_payload: dict[str, Any],
    published_post: Post,
) -> None:
    """POST /api/admin/posts/<id>/unpublish returns 200 with confirmation message."""
    mock_clerk, mock_user_repo = _auth_patches(admin_jwt_payload, admin_user)
    mock_post_repo = MagicMock()
    mock_post_repo.find_by_id.return_value = published_post
    mock_handler = MagicMock()
    mock_handler.handle.return_value = published_post

    with (
        patch(
            "backend.api.middleware.auth_middleware._get_clerk_adapter",
            return_value=mock_clerk,
        ),
        patch(
            "backend.api.middleware.auth_middleware._get_user_repository",
            return_value=mock_user_repo,
        ),
        patch(
            "backend.api.routes.admin._get_post_repository",
            return_value=mock_post_repo,
        ),
        patch(
            "backend.api.routes.admin._get_unpublish_post_handler",
            return_value=mock_handler,
        ),
    ):
        response = client.post(
            f"/api/admin/posts/{published_post.id}/unpublish",
            headers={"Authorization": "Bearer admin_token"},
        )

    assert response.status_code == 200
    assert "message" in response.json
    assert response.json["message"] == "Post unpublished"


def test_unpublish_missing_post_returns_404(
    client: Any,
    admin_user: User,
    admin_jwt_payload: dict[str, Any],
) -> None:
    """POST /api/admin/posts/99999/unpublish returns 404 when post does not exist."""
    mock_clerk, mock_user_repo = _auth_patches(admin_jwt_payload, admin_user)
    mock_post_repo = MagicMock()
    mock_post_repo.find_by_id.return_value = None

    with (
        patch(
            "backend.api.middleware.auth_middleware._get_clerk_adapter",
            return_value=mock_clerk,
        ),
        patch(
            "backend.api.middleware.auth_middleware._get_user_repository",
            return_value=mock_user_repo,
        ),
        patch(
            "backend.api.routes.admin._get_post_repository",
            return_value=mock_post_repo,
        ),
    ):
        response = client.post(
            "/api/admin/posts/99999/unpublish",
            headers={"Authorization": "Bearer admin_token"},
        )

    assert response.status_code == 404
    assert "error" in response.json


def test_unpublish_already_unpublished_post_returns_400(
    client: Any,
    admin_user: User,
    admin_jwt_payload: dict[str, Any],
    draft_post: Post,
) -> None:
    """POST /api/admin/posts/<id>/unpublish returns 400 for already-unpublished post."""
    mock_clerk, mock_user_repo = _auth_patches(admin_jwt_payload, admin_user)
    mock_post_repo = MagicMock()
    mock_post_repo.find_by_id.return_value = draft_post
    mock_handler = MagicMock()
    mock_handler.handle.side_effect = ValueError("Post already unpublished")

    with (
        patch(
            "backend.api.middleware.auth_middleware._get_clerk_adapter",
            return_value=mock_clerk,
        ),
        patch(
            "backend.api.middleware.auth_middleware._get_user_repository",
            return_value=mock_user_repo,
        ),
        patch(
            "backend.api.routes.admin._get_post_repository",
            return_value=mock_post_repo,
        ),
        patch(
            "backend.api.routes.admin._get_unpublish_post_handler",
            return_value=mock_handler,
        ),
    ):
        response = client.post(
            f"/api/admin/posts/{draft_post.id}/unpublish",
            headers={"Authorization": "Bearer admin_token"},
        )

    assert response.status_code == 400
    assert "error" in response.json
    assert "already unpublished" in response.json["error"].lower()


def test_unpublish_handler_not_found_error_returns_404(
    client: Any,
    admin_user: User,
    admin_jwt_payload: dict[str, Any],
    published_post: Post,
) -> None:
    """NotFoundError from handler maps to 404."""
    mock_clerk, mock_user_repo = _auth_patches(admin_jwt_payload, admin_user)
    mock_handler = MagicMock()
    mock_handler.handle.side_effect = NotFoundError("Post not found")

    with (
        patch(
            "backend.api.middleware.auth_middleware._get_clerk_adapter",
            return_value=mock_clerk,
        ),
        patch(
            "backend.api.middleware.auth_middleware._get_user_repository",
            return_value=mock_user_repo,
        ),
        patch(
            "backend.api.routes.admin._get_unpublish_post_handler",
            return_value=mock_handler,
        ),
    ):
        response = client.post(
            f"/api/admin/posts/{published_post.id}/unpublish",
            headers={"Authorization": "Bearer admin_token"},
        )

    assert response.status_code == 404
    assert "error" in response.json


# ---------------------------------------------------------------------------
# Section 7 – User activity endpoint (Req 8.3)
# ---------------------------------------------------------------------------


def test_user_activity_admin_success(
    client: Any,
    admin_user: User,
    admin_jwt_payload: dict[str, Any],
) -> None:
    """GET /api/admin/users/<id>/activity returns 200 with aggregated activity data."""
    mock_clerk, mock_user_repo = _auth_patches(admin_jwt_payload, admin_user)

    activity = UserActivity(
        last_login=datetime(2024, 5, 15, 10, 0, 0, tzinfo=UTC),
        posts_count=3,
        comments_count=12,
        recent_posts=[],
        recent_comments=[],
    )
    mock_handler = MagicMock()
    mock_handler.handle.return_value = activity

    with (
        patch(
            "backend.api.middleware.auth_middleware._get_clerk_adapter",
            return_value=mock_clerk,
        ),
        patch(
            "backend.api.middleware.auth_middleware._get_user_repository",
            return_value=mock_user_repo,
        ),
        patch(
            "backend.api.routes.admin._get_user_activity_handler",
            return_value=mock_handler,
        ),
    ):
        response = client.get(
            "/api/admin/users/7/activity",
            headers={"Authorization": "Bearer admin_token"},
        )

    assert response.status_code == 200
    body = response.json
    assert "user_id" in body
    assert "posts_count" in body
    assert "comments_count" in body
    assert body["user_id"] == 7
    assert body["posts_count"] == 3
    assert body["comments_count"] == 12


def test_user_activity_includes_last_login_field(
    client: Any,
    admin_user: User,
    admin_jwt_payload: dict[str, Any],
) -> None:
    """User activity response includes last_login (may be None)."""
    mock_clerk, mock_user_repo = _auth_patches(admin_jwt_payload, admin_user)

    activity = UserActivity(
        last_login=None,
        posts_count=0,
        comments_count=0,
        recent_posts=[],
        recent_comments=[],
    )
    mock_handler = MagicMock()
    mock_handler.handle.return_value = activity

    with (
        patch(
            "backend.api.middleware.auth_middleware._get_clerk_adapter",
            return_value=mock_clerk,
        ),
        patch(
            "backend.api.middleware.auth_middleware._get_user_repository",
            return_value=mock_user_repo,
        ),
        patch(
            "backend.api.routes.admin._get_user_activity_handler",
            return_value=mock_handler,
        ),
    ):
        response = client.get(
            "/api/admin/users/7/activity",
            headers={"Authorization": "Bearer admin_token"},
        )

    assert response.status_code == 200
    assert "last_login" in response.json


def test_user_activity_not_found_returns_404(
    client: Any,
    admin_user: User,
    admin_jwt_payload: dict[str, Any],
) -> None:
    """GET /api/admin/users/99999/activity returns 404 for unknown user."""
    mock_clerk, mock_user_repo = _auth_patches(admin_jwt_payload, admin_user)
    mock_handler = MagicMock()
    mock_handler.handle.side_effect = NotFoundError("User not found")

    with (
        patch(
            "backend.api.middleware.auth_middleware._get_clerk_adapter",
            return_value=mock_clerk,
        ),
        patch(
            "backend.api.middleware.auth_middleware._get_user_repository",
            return_value=mock_user_repo,
        ),
        patch(
            "backend.api.routes.admin._get_user_activity_handler",
            return_value=mock_handler,
        ),
    ):
        response = client.get(
            "/api/admin/users/99999/activity",
            headers={"Authorization": "Bearer admin_token"},
        )

    assert response.status_code == 404
    assert "error" in response.json


# ---------------------------------------------------------------------------
# Section 8 – 500 errors are captured by ErrorLogger (Req 8.5)
# ---------------------------------------------------------------------------


def test_unexpected_exception_in_system_health_is_logged(
    client: Any,
    admin_user: User,
    admin_jwt_payload: dict[str, Any],
) -> None:
    """Unhandled exception inside an admin route is captured by ErrorLogger."""
    mock_clerk, mock_user_repo = _auth_patches(admin_jwt_payload, admin_user)
    mock_handler = MagicMock()
    mock_handler.handle.side_effect = RuntimeError("db connection lost")

    with (
        patch(
            "backend.api.middleware.auth_middleware._get_clerk_adapter",
            return_value=mock_clerk,
        ),
        patch(
            "backend.api.middleware.auth_middleware._get_user_repository",
            return_value=mock_user_repo,
        ),
        patch(
            "backend.api.routes.admin._get_system_health_handler",
            return_value=mock_handler,
        ),
    ):
        response = client.get(
            "/api/admin/system/health",
            headers={"Authorization": "Bearer admin_token"},
        )

    assert response.status_code == 500
    recent = ErrorLogger.get_recent_errors(limit=1)
    assert len(recent) == 1
    assert "db connection lost" in recent[0].message


def test_unexpected_exception_in_user_activity_is_logged(
    client: Any,
    admin_user: User,
    admin_jwt_payload: dict[str, Any],
) -> None:
    """Unhandled exception inside user activity route is captured by ErrorLogger."""
    mock_clerk, mock_user_repo = _auth_patches(admin_jwt_payload, admin_user)
    mock_handler = MagicMock()
    mock_handler.handle.side_effect = RuntimeError("query timeout")

    with (
        patch(
            "backend.api.middleware.auth_middleware._get_clerk_adapter",
            return_value=mock_clerk,
        ),
        patch(
            "backend.api.middleware.auth_middleware._get_user_repository",
            return_value=mock_user_repo,
        ),
        patch(
            "backend.api.routes.admin._get_user_activity_handler",
            return_value=mock_handler,
        ),
    ):
        response = client.get(
            "/api/admin/users/1/activity",
            headers={"Authorization": "Bearer admin_token"},
        )

    assert response.status_code == 500
    recent = ErrorLogger.get_recent_errors(limit=1)
    assert len(recent) == 1
    assert "query timeout" in recent[0].message
