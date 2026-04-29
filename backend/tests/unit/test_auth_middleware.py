"""Unit tests for authentication middleware decorators.

This module provides comprehensive test coverage for Flask authentication
and authorization decorators following TDD red phase principles. Tests are
written before implementation and will initially fail.

Test Coverage:
- @require_auth decorator tests (9 tests)
- @require_role decorator tests (7 tests)
- Decorator composition tests (2 tests)

Total: 18 unit tests ensuring complete middleware behavior validation.
"""

from unittest.mock import Mock, patch

import pytest
from flask import Flask, g

from backend.domain.aggregates.user import User
from backend.domain.value_objects.role import Role
from backend.exceptions import AuthenticationError, AuthorizationError


@pytest.fixture
def app() -> Flask:
    """Create Flask test application instance.

    Returns:
        Configured Flask app with test configuration
    """
    test_app = Flask(__name__)
    test_app.config["TESTING"] = True
    return test_app


@pytest.fixture
def mock_adapter() -> Mock:
    """Create mock ClerkAuthAdapter instance.

    Returns:
        Mock adapter with verify_token method
    """
    adapter = Mock()
    adapter.verify_token = Mock()
    return adapter


@pytest.fixture
def mock_user_repository() -> Mock:
    """Create mock UserRepository instance.

    Returns:
        Mock repository with find_by_clerk_user_id and add methods
    """
    repository = Mock()
    repository.find_by_clerk_user_id = Mock()
    repository.add = Mock()
    return repository


@pytest.fixture
def authenticated_user() -> User:
    """Create test user with AUTHENTICATED role.

    Returns:
        User aggregate with AUTHENTICATED role
    """
    return User.create_from_clerk(
        clerk_user_id="user_2abc123", email="authenticated@example.com"
    )


@pytest.fixture
def author_user() -> User:
    """Create test user with AUTHOR role.

    Returns:
        User aggregate with AUTHOR role
    """
    user = User.create_from_clerk(
        clerk_user_id="user_2xyz789", email="author@example.com"
    )
    user.change_role(Role.AUTHOR)
    return user


@pytest.fixture
def admin_user() -> User:
    """Create test user with ADMIN role.

    Returns:
        User aggregate with ADMIN role
    """
    user = User.create_from_clerk(
        clerk_user_id="user_2admin999", email="admin@example.com"
    )
    user.change_role(Role.ADMIN)
    return user


def test_require_auth_with_valid_jwt_injects_user(
    app: Flask,
    mock_adapter: Mock,
    mock_user_repository: Mock,
    author_user: User,
) -> None:
    """Test require_auth extracts valid token and injects user into g object.

    Verifies that valid JWT token in Authorization header is extracted,
    validated via ClerkAuthAdapter, user is retrieved from repository,
    and injected into Flask g.current_user for downstream use.

    Args:
        app: Flask test application
        mock_adapter: Mocked ClerkAuthAdapter
        mock_user_repository: Mocked UserRepository
        author_user: User fixture with AUTHOR role
    """
    from backend.api.middleware.auth_middleware import require_auth

    mock_adapter.verify_token.return_value = {
        "sub": "user_2xyz789",
        "email": "author@example.com",
    }
    mock_user_repository.find_by_clerk_user_id.return_value = author_user

    @app.route("/test")
    @require_auth
    def test_endpoint() -> str:
        assert hasattr(g, "current_user")
        assert g.current_user.clerk_user_id == "user_2xyz789"
        assert g.current_user.role == Role.AUTHOR
        return "success"

    with app.test_request_context(
        "/test", headers={"Authorization": "Bearer valid_token_abc123"}
    ):
        with patch(
            "backend.api.middleware.auth_middleware.clerk_auth_adapter",
            mock_adapter,
        ):
            with patch(
                "backend.api.middleware.auth_middleware.user_repository",
                mock_user_repository,
            ):
                response = test_endpoint()

    assert response == "success"
    mock_adapter.verify_token.assert_called_once_with("valid_token_abc123")
    mock_user_repository.find_by_clerk_user_id.assert_called_once_with(
        "user_2xyz789"
    )


def test_require_auth_missing_authorization_header_returns_401(
    app: Flask, mock_adapter: Mock, mock_user_repository: Mock
) -> None:
    """Test require_auth returns 401 when Authorization header is missing.

    Verifies that request without Authorization header raises
    AuthenticationError before any token validation occurs.

    Args:
        app: Flask test application
        mock_adapter: Mocked ClerkAuthAdapter
        mock_user_repository: Mocked UserRepository
    """
    from backend.api.middleware.auth_middleware import require_auth

    @app.route("/test")
    @require_auth
    def test_endpoint() -> str:
        return "should_not_reach"

    with app.test_request_context("/test"):
        with patch(
            "backend.api.middleware.auth_middleware.clerk_auth_adapter",
            mock_adapter,
        ):
            with patch(
                "backend.api.middleware.auth_middleware.user_repository",
                mock_user_repository,
            ):
                with pytest.raises(AuthenticationError) as exc_info:
                    test_endpoint()

    assert "authorization header" in str(exc_info.value).lower()
    mock_adapter.verify_token.assert_not_called()


def test_require_auth_malformed_authorization_header_returns_401(
    app: Flask, mock_adapter: Mock, mock_user_repository: Mock
) -> None:
    """Test require_auth returns 401 for malformed Authorization header.

    Verifies that Authorization header without 'Bearer ' prefix or with
    invalid format raises AuthenticationError.

    Args:
        app: Flask test application
        mock_adapter: Mocked ClerkAuthAdapter
        mock_user_repository: Mocked UserRepository
    """
    from backend.api.middleware.auth_middleware import require_auth

    @app.route("/test")
    @require_auth
    def test_endpoint() -> str:
        return "should_not_reach"

    with app.test_request_context(
        "/test", headers={"Authorization": "InvalidFormat token123"}
    ):
        with patch(
            "backend.api.middleware.auth_middleware.clerk_auth_adapter",
            mock_adapter,
        ):
            with patch(
                "backend.api.middleware.auth_middleware.user_repository",
                mock_user_repository,
            ):
                with pytest.raises(AuthenticationError) as exc_info:
                    test_endpoint()

    assert (
        "invalid" in str(exc_info.value).lower()
        or "malformed" in str(exc_info.value).lower()
    )
    mock_adapter.verify_token.assert_not_called()


def test_require_auth_empty_token_string_returns_401(
    app: Flask, mock_adapter: Mock, mock_user_repository: Mock
) -> None:
    """Test require_auth returns 401 for empty token after Bearer prefix.

    Verifies that Authorization header with 'Bearer ' but empty token
    string raises AuthenticationError.

    Args:
        app: Flask test application
        mock_adapter: Mocked ClerkAuthAdapter
        mock_user_repository: Mocked UserRepository
    """
    from backend.api.middleware.auth_middleware import require_auth

    @app.route("/test")
    @require_auth
    def test_endpoint() -> str:
        return "should_not_reach"

    with app.test_request_context(
        "/test", headers={"Authorization": "Bearer "}
    ):
        with patch(
            "backend.api.middleware.auth_middleware.clerk_auth_adapter",
            mock_adapter,
        ):
            with patch(
                "backend.api.middleware.auth_middleware.user_repository",
                mock_user_repository,
            ):
                with pytest.raises(AuthenticationError) as exc_info:
                    test_endpoint()

    assert "token" in str(exc_info.value).lower()
    mock_adapter.verify_token.assert_not_called()


def test_require_auth_invalid_token_raises_authentication_error(
    app: Flask, mock_adapter: Mock, mock_user_repository: Mock
) -> None:
    """Test require_auth propagates AuthenticationError from adapter.

    Verifies that when ClerkAuthAdapter.verify_token raises
    AuthenticationError for invalid/expired token, the error
    propagates to caller.

    Args:
        app: Flask test application
        mock_adapter: Mocked ClerkAuthAdapter
        mock_user_repository: Mocked UserRepository
    """
    from backend.api.middleware.auth_middleware import require_auth

    mock_adapter.verify_token.side_effect = AuthenticationError("Token expired")

    @app.route("/test")
    @require_auth
    def test_endpoint() -> str:
        return "should_not_reach"

    with app.test_request_context(
        "/test", headers={"Authorization": "Bearer expired_token"}
    ):
        with patch(
            "backend.api.middleware.auth_middleware.clerk_auth_adapter",
            mock_adapter,
        ):
            with patch(
                "backend.api.middleware.auth_middleware.user_repository",
                mock_user_repository,
            ):
                with pytest.raises(AuthenticationError) as exc_info:
                    test_endpoint()

    assert "expired" in str(exc_info.value).lower()
    mock_adapter.verify_token.assert_called_once_with("expired_token")
    mock_user_repository.find_by_clerk_user_id.assert_not_called()


def test_require_auth_creates_first_time_user_in_database(
    app: Flask, mock_adapter: Mock, mock_user_repository: Mock
) -> None:
    """Test require_auth creates user on first authentication.

    Verifies that when user is not found in database, new User
    aggregate is created using create_from_clerk factory method
    and persisted via repository.add.

    Args:
        app: Flask test application
        mock_adapter: Mocked ClerkAuthAdapter
        mock_user_repository: Mocked UserRepository
    """
    from backend.api.middleware.auth_middleware import require_auth

    mock_adapter.verify_token.return_value = {
        "sub": "user_2newuser123",
        "email": "newuser@example.com",
    }
    mock_user_repository.find_by_clerk_user_id.return_value = None
    mock_user_repository.add.side_effect = lambda u: u

    @app.route("/test")
    @require_auth
    def test_endpoint() -> str:
        assert hasattr(g, "current_user")
        assert g.current_user.clerk_user_id == "user_2newuser123"
        assert g.current_user.email == "newuser@example.com"
        assert g.current_user.role == Role.AUTHENTICATED
        return "success"

    with app.test_request_context(
        "/test", headers={"Authorization": "Bearer new_user_token"}
    ):
        with patch(
            "backend.api.middleware.auth_middleware.clerk_auth_adapter",
            mock_adapter,
        ):
            with patch(
                "backend.api.middleware.auth_middleware.user_repository",
                mock_user_repository,
            ):
                response = test_endpoint()

    assert response == "success"
    mock_adapter.verify_token.assert_called_once_with("new_user_token")
    mock_user_repository.find_by_clerk_user_id.assert_called_once_with(
        "user_2newuser123"
    )
    mock_user_repository.add.assert_called_once()
    added_user = mock_user_repository.add.call_args[0][0]
    assert added_user.clerk_user_id == "user_2newuser123"
    assert added_user.email == "newuser@example.com"


def test_require_auth_retrieves_existing_user_from_database(
    app: Flask, mock_adapter: Mock, mock_user_repository: Mock, admin_user: User
) -> None:
    """Test require_auth retrieves existing user without creating duplicate.

    Verifies that when user exists in database, they are retrieved via
    find_by_clerk_user_id and repository.add is not called.

    Args:
        app: Flask test application
        mock_adapter: Mocked ClerkAuthAdapter
        mock_user_repository: Mocked UserRepository
        admin_user: Existing user fixture with ADMIN role
    """
    from backend.api.middleware.auth_middleware import require_auth

    mock_adapter.verify_token.return_value = {
        "sub": "user_2admin999",
        "email": "admin@example.com",
    }
    mock_user_repository.find_by_clerk_user_id.return_value = admin_user

    @app.route("/test")
    @require_auth
    def test_endpoint() -> str:
        assert hasattr(g, "current_user")
        assert g.current_user.clerk_user_id == "user_2admin999"
        assert g.current_user.role == Role.ADMIN
        return "success"

    with app.test_request_context(
        "/test", headers={"Authorization": "Bearer existing_user_token"}
    ):
        with patch(
            "backend.api.middleware.auth_middleware.clerk_auth_adapter",
            mock_adapter,
        ):
            with patch(
                "backend.api.middleware.auth_middleware.user_repository",
                mock_user_repository,
            ):
                response = test_endpoint()

    assert response == "success"
    mock_user_repository.find_by_clerk_user_id.assert_called_once_with(
        "user_2admin999"
    )
    mock_user_repository.add.assert_not_called()


def test_require_auth_preserves_flask_g_context_across_decorators(
    app: Flask,
    mock_adapter: Mock,
    mock_user_repository: Mock,
    author_user: User,
) -> None:
    """Test multiple decorated endpoints preserve g.current_user context.

    Verifies that Flask g object is properly managed across multiple
    decorator applications within same request context.

    Args:
        app: Flask test application
        mock_adapter: Mocked ClerkAuthAdapter
        mock_user_repository: Mocked UserRepository
        author_user: User fixture with AUTHOR role
    """
    from backend.api.middleware.auth_middleware import require_auth

    mock_adapter.verify_token.return_value = {
        "sub": "user_2xyz789",
        "email": "author@example.com",
    }
    mock_user_repository.find_by_clerk_user_id.return_value = author_user

    def inner_function() -> None:
        """Helper function to test g context preservation."""
        assert hasattr(g, "current_user")
        assert g.current_user.clerk_user_id == "user_2xyz789"

    @app.route("/test")
    @require_auth
    def test_endpoint() -> str:
        inner_function()
        assert g.current_user.role == Role.AUTHOR
        return "success"

    with app.test_request_context(
        "/test", headers={"Authorization": "Bearer valid_token"}
    ):
        with patch(
            "backend.api.middleware.auth_middleware.clerk_auth_adapter",
            mock_adapter,
        ):
            with patch(
                "backend.api.middleware.auth_middleware.user_repository",
                mock_user_repository,
            ):
                response = test_endpoint()

    assert response == "success"


def test_require_role_authenticated_allows_all_authenticated_users(
    app: Flask, authenticated_user: User
) -> None:
    """Test require_role with 'authenticated' allows all authenticated users.

    Verifies that require_role('authenticated') passes for any user
    who successfully passed @require_auth, regardless of specific role.

    Args:
        app: Flask test application
        authenticated_user: User with AUTHENTICATED role
    """
    from backend.api.middleware.auth_middleware import require_role

    @app.route("/test")
    @require_role("authenticated")
    def test_endpoint() -> str:
        return "success"

    with app.test_request_context("/test"):
        g.current_user = authenticated_user
        response = test_endpoint()

    assert response == "success"


def test_require_role_author_rejects_authenticated_role(
    app: Flask, authenticated_user: User
) -> None:
    """Test require_role with 'author' rejects AUTHENTICATED role users.

    Verifies that users with AUTHENTICATED role cannot access endpoints
    requiring AUTHOR role, raising AuthorizationError with 403 status.

    Args:
        app: Flask test application
        authenticated_user: User with AUTHENTICATED role
    """
    from backend.api.middleware.auth_middleware import require_role

    @app.route("/test")
    @require_role("author")
    def test_endpoint() -> str:
        return "should_not_reach"

    with app.test_request_context("/test"):
        g.current_user = authenticated_user
        with pytest.raises(AuthorizationError) as exc_info:
            test_endpoint()

    assert "author" in str(exc_info.value).lower()
    assert exc_info.value.required_role == "author"


def test_require_role_author_allows_admin_role_hierarchy(
    app: Flask, admin_user: User
) -> None:
    """Test require_role with 'author' allows ADMIN role via hierarchy.

    Verifies that ADMIN role can access AUTHOR endpoints due to
    role hierarchy where ADMIN has all AUTHOR permissions.

    Args:
        app: Flask test application
        admin_user: User with ADMIN role
    """
    from backend.api.middleware.auth_middleware import require_role

    @app.route("/test")
    @require_role("author")
    def test_endpoint() -> str:
        return "success"

    with app.test_request_context("/test"):
        g.current_user = admin_user
        response = test_endpoint()

    assert response == "success"


def test_require_role_admin_rejects_author_role(
    app: Flask, author_user: User
) -> None:
    """Test require_role with 'admin' rejects AUTHOR role users.

    Verifies that users with AUTHOR role cannot access endpoints
    requiring ADMIN role, raising AuthorizationError.

    Args:
        app: Flask test application
        author_user: User with AUTHOR role
    """
    from backend.api.middleware.auth_middleware import require_role

    @app.route("/test")
    @require_role("admin")
    def test_endpoint() -> str:
        return "should_not_reach"

    with app.test_request_context("/test"):
        g.current_user = author_user
        with pytest.raises(AuthorizationError) as exc_info:
            test_endpoint()

    assert "admin" in str(exc_info.value).lower()
    assert exc_info.value.required_role == "admin"


def test_require_role_admin_allows_admin_role(
    app: Flask, admin_user: User
) -> None:
    """Test require_role with 'admin' allows ADMIN role users.

    Verifies that users with ADMIN role can access admin-only endpoints.

    Args:
        app: Flask test application
        admin_user: User with ADMIN role
    """
    from backend.api.middleware.auth_middleware import require_role

    @app.route("/test")
    @require_role("admin")
    def test_endpoint() -> str:
        return "success"

    with app.test_request_context("/test"):
        g.current_user = admin_user
        response = test_endpoint()

    assert response == "success"


def test_require_role_without_authentication_returns_401_not_403(
    app: Flask,
) -> None:
    """Test require_role returns 401 when no user authenticated.

    Verifies that missing g.current_user (authentication not performed)
    raises AuthenticationError (401) rather than AuthorizationError (403).
    Authentication must occur before authorization.

    Args:
        app: Flask test application
    """
    from backend.api.middleware.auth_middleware import require_role

    @app.route("/test")
    @require_role("author")
    def test_endpoint() -> str:
        return "should_not_reach"

    with app.test_request_context("/test"):
        with pytest.raises(AuthenticationError) as exc_info:
            test_endpoint()

    assert (
        "authenticated" in str(exc_info.value).lower()
        or "not authenticated" in str(exc_info.value).lower()
    )


def test_require_role_uses_role_can_access_methods(
    app: Flask, author_user: User, admin_user: User
) -> None:
    """Test require_role delegates to Role.can_access_* methods.

    Verifies that require_role uses Role value object methods
    can_access_author_endpoints and can_access_admin_endpoints
    for authorization decisions.

    Args:
        app: Flask test application
        author_user: User with AUTHOR role
        admin_user: User with ADMIN role
    """
    from backend.api.middleware.auth_middleware import require_role

    @app.route("/author-endpoint")
    @require_role("author")
    def author_endpoint() -> str:
        return "author_success"

    @app.route("/admin-endpoint")
    @require_role("admin")
    def admin_endpoint() -> str:
        return "admin_success"

    with app.test_request_context("/author-endpoint"):
        g.current_user = author_user
        assert author_user.role.can_access_author_endpoints()
        response = author_endpoint()
        assert response == "author_success"

    with app.test_request_context("/admin-endpoint"):
        g.current_user = admin_user
        assert admin_user.role.can_access_admin_endpoints()
        response = admin_endpoint()
        assert response == "admin_success"

    with app.test_request_context("/admin-endpoint"):
        g.current_user = author_user
        assert not author_user.role.can_access_admin_endpoints()
        with pytest.raises(AuthorizationError):
            admin_endpoint()


def test_require_role_composes_with_require_auth_401_before_403(
    app: Flask, mock_adapter: Mock, mock_user_repository: Mock
) -> None:
    """Test decorator composition returns 401 before checking authorization.

    Verifies that when both @require_auth and @require_role are applied,
    authentication errors (401) are raised before authorization errors (403).

    Args:
        app: Flask test application
        mock_adapter: Mocked ClerkAuthAdapter
        mock_user_repository: Mocked UserRepository
    """
    from backend.api.middleware.auth_middleware import (
        require_auth,
        require_role,
    )

    @app.route("/test")
    @require_auth
    @require_role("admin")
    def test_endpoint() -> str:
        return "should_not_reach"

    with app.test_request_context("/test"):
        with patch(
            "backend.api.middleware.auth_middleware.clerk_auth_adapter",
            mock_adapter,
        ):
            with patch(
                "backend.api.middleware.auth_middleware.user_repository",
                mock_user_repository,
            ):
                with pytest.raises(AuthenticationError) as exc_info:
                    test_endpoint()

    assert "authorization header" in str(exc_info.value).lower()
    mock_adapter.verify_token.assert_not_called()


def test_g_current_user_available_after_both_decorators(
    app: Flask,
    mock_adapter: Mock,
    mock_user_repository: Mock,
    admin_user: User,
) -> None:
    """Test g.current_user available in endpoint after decorator composition.

    Verifies that when @require_auth and @require_role are both applied,
    g.current_user is properly populated and accessible in endpoint.

    Args:
        app: Flask test application
        mock_adapter: Mocked ClerkAuthAdapter
        mock_user_repository: Mocked UserRepository
        admin_user: User with ADMIN role
    """
    from backend.api.middleware.auth_middleware import (
        require_auth,
        require_role,
    )

    mock_adapter.verify_token.return_value = {
        "sub": "user_2admin999",
        "email": "admin@example.com",
    }
    mock_user_repository.find_by_clerk_user_id.return_value = admin_user

    @app.route("/test")
    @require_auth
    @require_role("admin")
    def test_endpoint() -> str:
        assert hasattr(g, "current_user")
        assert g.current_user.clerk_user_id == "user_2admin999"
        assert g.current_user.role == Role.ADMIN
        return "success"

    with app.test_request_context(
        "/test", headers={"Authorization": "Bearer admin_token"}
    ):
        with patch(
            "backend.api.middleware.auth_middleware.clerk_auth_adapter",
            mock_adapter,
        ):
            with patch(
                "backend.api.middleware.auth_middleware.user_repository",
                mock_user_repository,
            ):
                response = test_endpoint()

    assert response == "success"
    mock_adapter.verify_token.assert_called_once_with("admin_token")
    mock_user_repository.find_by_clerk_user_id.assert_called_once_with(
        "user_2admin999"
    )
