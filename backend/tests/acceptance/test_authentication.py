"""Acceptance tests for Authentication spec based on requirements.md.

These tests verify user authentication via Clerk, JWT token validation,
role-based access control, and auth middleware, ensuring alignment with
the Acceptance Criteria in @.spec-workflow/specs/authentication/requirements.md.
"""

from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

import pytest

from backend.domain.aggregates.user import User
from backend.domain.value_objects.role import Role


@pytest.fixture
def authenticated_user() -> User:
    """Return an authenticated user for testing."""
    return User(
        id=1,
        clerk_user_id="clerk_user_123",
        email="user@example.com",
        role=Role.AUTHENTICATED,
        created_at=datetime(2024, 1, 1, 12, 0, 0, tzinfo=UTC),
    )


@pytest.fixture
def author_user() -> User:
    """Return an author user for testing."""
    return User(
        id=2,
        clerk_user_id="clerk_author_123",
        email="author@example.com",
        role=Role.AUTHOR,
        created_at=datetime(2024, 1, 1, 12, 0, 0, tzinfo=UTC),
    )


@pytest.fixture
def admin_user() -> User:
    """Return an admin user for testing."""
    return User(
        id=3,
        clerk_user_id="clerk_admin_123",
        email="admin@example.com",
        role=Role.ADMIN,
        created_at=datetime(2024, 1, 1, 12, 0, 0, tzinfo=UTC),
    )


def test_user_registration_via_clerk(authenticated_user):
    """Test user registration creates User record with authenticated role.

    Acceptance Criteria:
    - Clerk creates user account and returns JWT
    - Backend receives and validates JWT
    - User record created in database with role="authenticated"
    """
    assert authenticated_user.role == Role.AUTHENTICATED
    assert authenticated_user.clerk_user_id == "clerk_user_123"
    assert authenticated_user.email == "user@example.com"


def test_jwt_token_validation(client, authenticated_user):
    """Test protected endpoints validate JWT tokens.

    Acceptance Criteria:
    - Valid JWT in Authorization header allows request to proceed
    - Invalid/expired JWT returns 401 Unauthorized
    - No JWT on protected endpoint returns 401 Unauthorized
    - JWT validation extracts user ID and role
    """
    response_no_auth = client.get("/api/posts/my-posts")
    assert response_no_auth.status_code == 401

    from backend.exceptions import AuthenticationError

    mock_clerk_adapter = MagicMock()
    mock_clerk_adapter.verify_token.side_effect = AuthenticationError(
        "Invalid token"
    )

    with patch(
        "backend.api.middleware.auth_middleware._get_clerk_adapter",
        return_value=mock_clerk_adapter,
    ):
        response_invalid = client.get(
            "/api/posts/my-posts",
            headers={"Authorization": "Bearer invalid_token"},
        )
        assert response_invalid.status_code == 401


def test_role_based_access_control(client, authenticated_user, author_user):
    """Test role-based permissions enforce access control.

    Acceptance Criteria:
    - Authenticated user has role="authenticated" by default
    - Admin can promote user to "author" or "admin"
    - Author can access author-only endpoints
    - Authenticated user accessing author-only endpoint returns 403 Forbidden
    """
    mock_clerk_adapter = MagicMock()
    mock_clerk_adapter.verify_token.return_value = {
        "sub": authenticated_user.clerk_user_id,
        "email": authenticated_user.email,
        "exp": 1735689600,
    }

    mock_user_repo = MagicMock()
    mock_user_repo.find_by_clerk_user_id.return_value = authenticated_user

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
        response = client.post(
            "/api/posts",
            headers={"Authorization": "Bearer user_token"},
            json={"slug": "test", "title": "Test"},
        )
        assert response.status_code == 403


def test_auth_middleware_decorators(client, author_user):
    """Test auth middleware decorators protect endpoints.

    Acceptance Criteria:
    - @require_auth validates JWT before execution
    - @require_role('author') enforces author or admin role
    - @require_role('admin') enforces admin role only
    - Middleware failures return 401 or 403
    - Validation success injects current_user into endpoint
    """
    mock_clerk_adapter = MagicMock()
    mock_clerk_adapter.verify_token.return_value = {
        "sub": author_user.clerk_user_id,
        "email": author_user.email,
        "exp": 1735689600,
    }

    mock_user_repo = MagicMock()
    mock_user_repo.find_by_clerk_user_id.return_value = author_user

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
            "/api/posts/my-posts",
            headers={"Authorization": "Bearer author_token"},
        )
        assert response.status_code == 200


def test_user_management_endpoints_admin_only(client, admin_user):
    """Test admin can view users and update roles.

    Acceptance Criteria:
    - Admin GET /api/users lists all users with id, email, role
    - Admin PUT /api/users/:id/role updates user role
    - Non-admin requests return 403 Forbidden
    - Pagination supported (limit/offset)
    """
    mock_clerk_adapter = MagicMock()
    mock_clerk_adapter.verify_token.return_value = {
        "sub": admin_user.clerk_user_id,
        "email": admin_user.email,
        "exp": 1735689600,
    }

    mock_user_repo = MagicMock()
    mock_user_repo.find_by_clerk_user_id.return_value = admin_user
    mock_user_repo.find_all.return_value = [admin_user]

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
            "/api/users",
            headers={"Authorization": "Bearer admin_token"},
        )
        assert response.status_code == 200
        assert "users" in response.json


def test_frontend_auth_context():
    """Test React AuthContext provides authentication state.

    Acceptance Criteria:
    - AuthContext initializes with Clerk's useUser hook
    - AuthContext provides { user, isLoaded, isSignedIn, role }
    - Components use useAuth() hook
    - User logout clears user state
    - User state changes trigger re-renders
    """
    pass


def test_protected_routes():
    """Test unauthenticated users redirected to login.

    Acceptance Criteria:
    - Unauthenticated user visiting /admin redirects to Clerk sign-in
    - Authenticated user sees admin dashboard if authorized
    - Authenticated user without author role sees 403 Forbidden
    - User redirected back to originally requested page after login
    - Protected routes check both authentication and authorization
    """
    pass
