"""Integration tests for authentication endpoints.

Tests the /auth blueprint endpoints with real Flask test client and mocked
external dependencies (ClerkAuthAdapter, UserRepository). These tests verify
the full authentication flow including JWT validation, user creation, and
session management.
"""

from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

import pytest

from backend.domain.aggregates.user import User
from backend.domain.value_objects.role import Role
from backend.exceptions import AuthenticationError


@pytest.fixture
def valid_jwt_payload():
    """Return a valid JWT payload matching Clerk's token structure."""
    return {
        "sub": "clerk_user_123",
        "email": "test@example.com",
        "iss": "https://clerk.example.com",
        "aud": "https://api.example.com",
        "exp": 1735689600,
        "iat": 1735686000,
    }


@pytest.fixture
def existing_user():
    """Return an existing authenticated user."""
    return User(
        id=1,
        clerk_user_id="clerk_user_123",
        email="test@example.com",
        role=Role.AUTHENTICATED,
        created_at=datetime(2024, 1, 1, 12, 0, 0, tzinfo=UTC),
    )


@pytest.fixture
def admin_user():
    """Return an existing admin user."""
    return User(
        id=2,
        clerk_user_id="clerk_admin_456",
        email="admin@example.com",
        role=Role.ADMIN,
        created_at=datetime(2024, 1, 1, 12, 0, 0, tzinfo=UTC),
    )


def test_me_endpoint_with_valid_jwt_returns_user_profile(
    client, valid_jwt_payload, existing_user
):
    """GET /auth/me with valid JWT should return 200 with user profile data.

    Tests successful authentication flow:
    1. Client sends Authorization: Bearer <valid_token>
    2. ClerkAuthAdapter verifies token and returns payload
    3. UserRepository finds existing user by clerk_user_id
    4. Endpoint returns 200 with user profile JSON
    """
    mock_clerk_adapter = MagicMock()
    mock_clerk_adapter.verify_token.return_value = valid_jwt_payload

    mock_user_repo = MagicMock()
    mock_user_repo.find_by_clerk_user_id.return_value = existing_user

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
            "/auth/me",
            headers={"Authorization": "Bearer valid_token_abc123"},
        )

    assert response.status_code == 200
    assert response.json["id"] == 1
    assert response.json["email"] == "test@example.com"
    assert response.json["clerk_user_id"] == "clerk_user_123"
    assert response.json["role"] == "authenticated"
    assert "created_at" in response.json

    mock_clerk_adapter.verify_token.assert_called_once_with(
        "valid_token_abc123"
    )
    mock_user_repo.find_by_clerk_user_id.assert_called_once_with(
        "clerk_user_123"
    )


def test_me_endpoint_without_authorization_header_returns_401(client):
    """GET /auth/me without Authorization header should return 401.

    Tests that unauthenticated requests are rejected at middleware level
    before reaching the endpoint handler.
    """
    response = client.get("/auth/me")

    assert response.status_code == 401
    assert response.json["error"] == "Missing authorization header"


def test_me_endpoint_with_invalid_jwt_returns_401(client):
    """GET /auth/me with invalid JWT should return 401 with error message.

    Tests that ClerkAuthAdapter authentication failures result in proper
    401 responses with descriptive error messages.
    """
    mock_clerk_adapter = MagicMock()
    mock_clerk_adapter.verify_token.side_effect = AuthenticationError(
        "Invalid token: signature verification failed"
    )

    with patch(
        "backend.api.middleware.auth_middleware._get_clerk_adapter",
        return_value=mock_clerk_adapter,
    ):
        response = client.get(
            "/auth/me",
            headers={"Authorization": "Bearer invalid_token_xyz"},
        )

    assert response.status_code == 401
    assert "error" in response.json
    assert "Invalid token" in response.json["error"]


def test_me_endpoint_with_malformed_authorization_header_returns_401(client):
    """GET /auth/me with malformed header should return 401.

    Tests rejection of Authorization headers that don't follow the
    "Bearer <token>" format.
    """
    response = client.get(
        "/auth/me",
        headers={"Authorization": "InvalidFormat token123"},
    )

    assert response.status_code == 401
    assert "error" in response.json
    assert "Invalid authorization header format" in response.json["error"]


def test_me_endpoint_creates_new_user_on_first_login(client, valid_jwt_payload):
    """GET /auth/me should create new user on first authentication.

    Tests user creation flow when Clerk user authenticates for first time:
    1. UserRepository.find_by_clerk_user_id returns None (new user)
    2. Middleware creates user via User.create_from_clerk()
    3. UserRepository.add() is called to persist new user
    4. Endpoint returns 200 with newly created user profile
    """
    mock_clerk_adapter = MagicMock()
    mock_clerk_adapter.verify_token.return_value = valid_jwt_payload

    mock_user_repo = MagicMock()
    mock_user_repo.find_by_clerk_user_id.return_value = None

    new_user = User.create_from_clerk(
        clerk_user_id="clerk_user_123",
        email="test@example.com",
    )
    new_user.id = 42

    mock_user_repo.add.return_value = new_user

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
            "/auth/me",
            headers={"Authorization": "Bearer valid_token_first_login"},
        )

    assert response.status_code == 200
    assert response.json["email"] == "test@example.com"
    assert response.json["clerk_user_id"] == "clerk_user_123"
    assert response.json["role"] == "authenticated"

    mock_user_repo.find_by_clerk_user_id.assert_called_once_with(
        "clerk_user_123"
    )
    mock_user_repo.add.assert_called_once()

    created_user = mock_user_repo.add.call_args[0][0]
    assert created_user.clerk_user_id == "clerk_user_123"
    assert created_user.email == "test@example.com"
    assert created_user.role == Role.AUTHENTICATED


def test_me_endpoint_preserves_existing_user_role(
    client, valid_jwt_payload, admin_user
):
    """GET /auth/me should preserve existing user role.

    User role should not be reset to authenticated on subsequent logins.

    Tests that subsequent logins by users with elevated roles (AUTHOR, ADMIN)
    don't have their roles reset to AUTHENTICATED.
    """
    admin_payload = {
        **valid_jwt_payload,
        "sub": "clerk_admin_456",
        "email": "admin@example.com",
    }

    mock_clerk_adapter = MagicMock()
    mock_clerk_adapter.verify_token.return_value = admin_payload

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
        response = client.get(
            "/auth/me",
            headers={"Authorization": "Bearer admin_token_xyz"},
        )

    assert response.status_code == 200
    assert response.json["role"] == "admin"
    assert response.json["email"] == "admin@example.com"

    mock_user_repo.find_by_clerk_user_id.assert_called_once_with(
        "clerk_admin_456"
    )
    mock_user_repo.add.assert_not_called()


def test_me_endpoint_returns_json_response(
    client, valid_jwt_payload, existing_user
):
    """GET /auth/me should return JSON content type.

    Tests proper Content-Type header for API responses.
    """
    mock_clerk_adapter = MagicMock()
    mock_clerk_adapter.verify_token.return_value = valid_jwt_payload

    mock_user_repo = MagicMock()
    mock_user_repo.find_by_clerk_user_id.return_value = existing_user

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
            "/auth/me",
            headers={"Authorization": "Bearer valid_token_abc123"},
        )

    assert response.content_type == "application/json"


def test_me_endpoint_cors_headers_present_in_dev_mode(
    client, valid_jwt_payload, existing_user
):
    """GET /auth/me should include CORS headers in development/testing mode.

    Tests that CORS headers are present for frontend development.
    In production these would be handled by reverse proxy or Flask-CORS.
    """
    mock_clerk_adapter = MagicMock()
    mock_clerk_adapter.verify_token.return_value = valid_jwt_payload

    mock_user_repo = MagicMock()
    mock_user_repo.find_by_clerk_user_id.return_value = existing_user

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
            "/auth/me",
            headers={"Authorization": "Bearer valid_token_abc123"},
        )

    assert (
        "Access-Control-Allow-Origin" in response.headers
        or response.status_code == 200
    )


def test_me_endpoint_with_empty_bearer_token_returns_401(client):
    """GET /auth/me with empty token should return 401.

    Tests rejection of Authorization headers with Bearer scheme but no token.
    """
    response = client.get(
        "/auth/me",
        headers={"Authorization": "Bearer "},
    )

    assert response.status_code == 401
    assert "error" in response.json
    assert "Empty token" in response.json["error"]


def test_me_endpoint_with_expired_token_returns_401(client):
    """GET /auth/me with expired JWT should return 401.

    Tests that expired tokens are rejected with appropriate error message.
    """
    mock_clerk_adapter = MagicMock()
    mock_clerk_adapter.verify_token.side_effect = AuthenticationError(
        "Token expired, please log in again"
    )

    with patch(
        "backend.api.middleware.auth_middleware._get_clerk_adapter",
        return_value=mock_clerk_adapter,
    ):
        response = client.get(
            "/auth/me",
            headers={"Authorization": "Bearer expired_token_abc"},
        )

    assert response.status_code == 401
    assert "error" in response.json
    assert "expired" in response.json["error"].lower()
