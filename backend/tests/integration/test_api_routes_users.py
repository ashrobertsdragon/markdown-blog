"""Integration tests for users management endpoints.

Tests the /users blueprint endpoints with real Flask test client and mocked
UserRepository. Verifies full request/response flow including middleware,
parameter validation, and error handling.
"""

from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

import pytest

from backend.domain.aggregates.user import User
from backend.domain.value_objects.role import Role


@pytest.fixture
def admin_user():
    """Return an existing admin user for testing."""
    return User(
        id=1,
        clerk_user_id="clerk_admin_123",
        email="admin@example.com",
        role=Role.ADMIN,
        created_at=datetime(2024, 1, 1, 12, 0, 0, tzinfo=UTC),
    )


@pytest.fixture
def regular_user():
    """Return an existing authenticated user for testing."""
    return User(
        id=5,
        clerk_user_id="clerk_user_456",
        email="user@example.com",
        role=Role.AUTHENTICATED,
        created_at=datetime(2024, 2, 1, 12, 0, 0, tzinfo=UTC),
    )


@pytest.fixture
def admin_jwt_payload():
    """Return a valid admin JWT payload."""
    return {
        "sub": "clerk_admin_123",
        "email": "admin@example.com",
        "exp": 1735689600,
    }


def test_list_users_with_admin_token_returns_200(
    client, admin_user, admin_jwt_payload
):
    """GET /users with admin token should return 200 with users list."""
    mock_clerk_adapter = MagicMock()
    mock_clerk_adapter.verify_token.return_value = admin_jwt_payload

    mock_user_repo = MagicMock()
    mock_user_repo.find_by_clerk_user_id.return_value = admin_user
    mock_user_repo.list_all.return_value = [admin_user]

    with (
        patch(
            "backend.api.middleware.auth_middleware._get_clerk_adapter",
            return_value=mock_clerk_adapter,
        ),
        patch(
            "backend.api.middleware.auth_middleware._get_user_repository",
            return_value=mock_user_repo,
        ),
        patch(
            "backend.api.routes.users._get_user_repository",
            return_value=mock_user_repo,
        ),
    ):
        response = client.get(
            "/users",
            headers={"Authorization": "Bearer admin_token_123"},
        )

    assert response.status_code == 200
    assert "users" in response.json
    assert isinstance(response.json["users"], list)
    assert "limit" in response.json
    assert "offset" in response.json


def test_list_users_without_auth_returns_401(client):
    """GET /users without Authorization header should return 401."""
    response = client.get("/users")

    assert response.status_code == 401
    assert "error" in response.json


def test_list_users_with_non_admin_returns_403(
    client, regular_user, admin_jwt_payload
):
    """GET /users with non-admin user should return 403."""
    regular_payload = {
        **admin_jwt_payload,
        "sub": "clerk_user_456",
        "email": "user@example.com",
    }

    mock_clerk_adapter = MagicMock()
    mock_clerk_adapter.verify_token.return_value = regular_payload

    mock_user_repo = MagicMock()
    mock_user_repo.find_by_clerk_user_id.return_value = regular_user

    with (
        patch(
            "backend.api.middleware.auth_middleware._get_clerk_adapter",
            return_value=mock_clerk_adapter,
        ),
        patch(
            "backend.api.middleware.auth_middleware._get_user_repository",
            return_value=mock_user_repo,
        ),
    ):
        response = client.get(
            "/users",
            headers={"Authorization": "Bearer user_token_456"},
        )

    assert response.status_code == 403


def test_list_users_pagination_parameters_work(
    client, admin_user, admin_jwt_payload
):
    """GET /users with pagination parameters passes them to repository."""
    mock_clerk_adapter = MagicMock()
    mock_clerk_adapter.verify_token.return_value = admin_jwt_payload

    mock_user_repo = MagicMock()
    mock_user_repo.find_by_clerk_user_id.return_value = admin_user
    mock_user_repo.list_all.return_value = []

    with (
        patch(
            "backend.api.middleware.auth_middleware._get_clerk_adapter",
            return_value=mock_clerk_adapter,
        ),
        patch(
            "backend.api.middleware.auth_middleware._get_user_repository",
            return_value=mock_user_repo,
        ),
        patch(
            "backend.api.routes.users._get_user_repository",
            return_value=mock_user_repo,
        ),
    ):
        response = client.get(
            "/users?limit=25&offset=50",
            headers={"Authorization": "Bearer admin_token_123"},
        )

    assert response.status_code == 200
    assert response.json["limit"] == 25
    assert response.json["offset"] == 50
    mock_user_repo.list_all.assert_called_with(limit=25, offset=50)


def test_update_user_role_with_admin_token_returns_200(
    client, admin_user, regular_user, admin_jwt_payload
):
    """PUT /users/:id/role with admin token returns 200 with updated user."""
    mock_clerk_adapter = MagicMock()
    mock_clerk_adapter.verify_token.return_value = admin_jwt_payload

    mock_user_repo = MagicMock()
    mock_user_repo.find_by_clerk_user_id.return_value = admin_user
    mock_user_repo.find_by_id.return_value = regular_user
    mock_user_repo.save.return_value = regular_user

    with (
        patch(
            "backend.api.middleware.auth_middleware._get_clerk_adapter",
            return_value=mock_clerk_adapter,
        ),
        patch(
            "backend.api.middleware.auth_middleware._get_user_repository",
            return_value=mock_user_repo,
        ),
        patch(
            "backend.api.routes.users._get_user_repository",
            return_value=mock_user_repo,
        ),
    ):
        response = client.put(
            "/users/5/role",
            headers={"Authorization": "Bearer admin_token_123"},
            json={"role": "author"},
        )

    assert response.status_code == 200
    assert "user" in response.json
    assert response.json["user"]["role"] == "author"
    mock_user_repo.save.assert_called_once()


def test_update_user_role_invalid_role_returns_400(
    client, admin_user, admin_jwt_payload
):
    """PUT /users/:id/role with invalid role should return 400."""
    mock_clerk_adapter = MagicMock()
    mock_clerk_adapter.verify_token.return_value = admin_jwt_payload

    mock_user_repo = MagicMock()
    mock_user_repo.find_by_clerk_user_id.return_value = admin_user

    with (
        patch(
            "backend.api.middleware.auth_middleware._get_clerk_adapter",
            return_value=mock_clerk_adapter,
        ),
        patch(
            "backend.api.middleware.auth_middleware._get_user_repository",
            return_value=mock_user_repo,
        ),
    ):
        response = client.put(
            "/users/5/role",
            headers={"Authorization": "Bearer admin_token_123"},
            json={"role": "superadmin"},
        )

    assert response.status_code == 400
    assert "Invalid role value" in response.json["error"]


def test_update_user_role_user_not_found_returns_404(
    client, admin_user, admin_jwt_payload
):
    """PUT /users/:id/role for non-existent user should return 404."""
    mock_clerk_adapter = MagicMock()
    mock_clerk_adapter.verify_token.return_value = admin_jwt_payload

    mock_user_repo = MagicMock()
    mock_user_repo.find_by_clerk_user_id.return_value = admin_user
    mock_user_repo.find_by_id.return_value = None

    with (
        patch(
            "backend.api.middleware.auth_middleware._get_clerk_adapter",
            return_value=mock_clerk_adapter,
        ),
        patch(
            "backend.api.middleware.auth_middleware._get_user_repository",
            return_value=mock_user_repo,
        ),
        patch(
            "backend.api.routes.users._get_user_repository",
            return_value=mock_user_repo,
        ),
    ):
        response = client.put(
            "/users/999/role",
            headers={"Authorization": "Bearer admin_token_123"},
            json={"role": "author"},
        )

    assert response.status_code == 404
    assert "not found" in response.json["error"]


def test_update_user_role_without_auth_returns_401(client):
    """PUT /users/:id/role without Authorization header should return 401."""
    response = client.put("/users/5/role", json={"role": "author"})

    assert response.status_code == 401
    assert "error" in response.json


def test_update_user_role_with_non_admin_returns_403(
    client, regular_user, admin_jwt_payload
):
    """PUT /users/:id/role with non-admin user should return 403."""
    regular_payload = {
        **admin_jwt_payload,
        "sub": "clerk_user_456",
        "email": "user@example.com",
    }

    mock_clerk_adapter = MagicMock()
    mock_clerk_adapter.verify_token.return_value = regular_payload

    mock_user_repo = MagicMock()
    mock_user_repo.find_by_clerk_user_id.return_value = regular_user

    with (
        patch(
            "backend.api.middleware.auth_middleware._get_clerk_adapter",
            return_value=mock_clerk_adapter,
        ),
        patch(
            "backend.api.middleware.auth_middleware._get_user_repository",
            return_value=mock_user_repo,
        ),
    ):
        response = client.put(
            "/users/5/role",
            headers={"Authorization": "Bearer user_token_456"},
            json={"role": "author"},
        )

    assert response.status_code == 403


def test_list_users_returns_correct_json_structure(
    client, admin_user, admin_jwt_payload
):
    """GET /users should return JSON with correct structure."""
    mock_clerk_adapter = MagicMock()
    mock_clerk_adapter.verify_token.return_value = admin_jwt_payload

    mock_user_repo = MagicMock()
    mock_user_repo.find_by_clerk_user_id.return_value = admin_user
    mock_user_repo.list_all.return_value = [admin_user]

    with (
        patch(
            "backend.api.middleware.auth_middleware._get_clerk_adapter",
            return_value=mock_clerk_adapter,
        ),
        patch(
            "backend.api.middleware.auth_middleware._get_user_repository",
            return_value=mock_user_repo,
        ),
        patch(
            "backend.api.routes.users._get_user_repository",
            return_value=mock_user_repo,
        ),
    ):
        response = client.get(
            "/users",
            headers={"Authorization": "Bearer admin_token_123"},
        )

    assert response.status_code == 200
    assert response.content_type == "application/json"
    assert len(response.json["users"]) == 1
    user = response.json["users"][0]
    assert "id" in user
    assert "email" in user
    assert "role" in user
    assert "clerk_user_id" in user
    assert "created_at" in user


def test_update_user_role_missing_request_body_returns_415(
    client, admin_user, admin_jwt_payload
):
    """PUT /users/:id/role without Content-Type returns 415."""
    mock_clerk_adapter = MagicMock()
    mock_clerk_adapter.verify_token.return_value = admin_jwt_payload

    mock_user_repo = MagicMock()
    mock_user_repo.find_by_clerk_user_id.return_value = admin_user

    with (
        patch(
            "backend.api.middleware.auth_middleware._get_clerk_adapter",
            return_value=mock_clerk_adapter,
        ),
        patch(
            "backend.api.middleware.auth_middleware._get_user_repository",
            return_value=mock_user_repo,
        ),
    ):
        response = client.put(
            "/users/5/role",
            headers={"Authorization": "Bearer admin_token_123"},
            data="",
        )

    assert response.status_code == 415


def test_update_user_role_missing_role_field_returns_400(
    client, admin_user, admin_jwt_payload
):
    """PUT /users/:id/role without role field should return 400."""
    mock_clerk_adapter = MagicMock()
    mock_clerk_adapter.verify_token.return_value = admin_jwt_payload

    mock_user_repo = MagicMock()
    mock_user_repo.find_by_clerk_user_id.return_value = admin_user

    with (
        patch(
            "backend.api.middleware.auth_middleware._get_clerk_adapter",
            return_value=mock_clerk_adapter,
        ),
        patch(
            "backend.api.middleware.auth_middleware._get_user_repository",
            return_value=mock_user_repo,
        ),
    ):
        response = client.put(
            "/users/5/role",
            headers={"Authorization": "Bearer admin_token_123"},
            json={},
        )

    assert response.status_code == 400
    assert "role field is required" in response.json["error"]
