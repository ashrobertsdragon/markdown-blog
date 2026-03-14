"""Authentication and authorization middleware decorators for Flask.

This module provides Flask decorators for JWT authentication and role-based
access control. Decorators extract and validate JWT tokens, retrieve or create
users, and enforce role-based permissions.

Decorators:
    @require_auth: Validates JWT and injects current user into Flask g object
    @require_role(role): Enforces role-based access control
        (composes with require_auth)

Architecture:
    - Uses ClerkAuthAdapter for JWT token verification
    - Uses UserRepository for user persistence
    - Injects authenticated user into Flask g.current_user
    - Raises AuthenticationError (401) for auth failures
    - Raises AuthorizationError (403) for permission failures

Usage:
    Authentication only:
        >>> @app.route("/profile")
        >>> @require_auth
        >>> def profile():
        ...     user = g.current_user
        ...     return {"email": user.email}

    Role-based authorization:
        >>> @app.route("/posts", methods=["POST"])
        >>> @require_role("author")
        >>> def create_post():
        ...     return create_post_for_user(g.current_user)

    Admin-only endpoints:
        >>> @app.route("/admin/users")
        >>> @require_role("admin")
        >>> def list_users():
        ...     return get_all_users()
"""

import logging
from collections.abc import Callable
from functools import wraps
from typing import Any

from flask import g, request

from backend.config import Settings
from backend.domain.aggregates.user import User
from backend.exceptions import AuthenticationError, AuthorizationError
from backend.infrastructure.auth.clerk_auth_adapter import ClerkAuthAdapter
from backend.infrastructure.persistence.user_repository import UserRepository

_settings: Settings | None = None
_clerk_adapter: ClerkAuthAdapter | None = None
_user_repo: UserRepository | None = None


def _get_settings() -> Settings:
    """Lazily initialize Settings instance.

    Returns:
        Settings instance (singleton pattern)
    """
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings


def _get_clerk_adapter() -> ClerkAuthAdapter:
    """Lazily initialize ClerkAuthAdapter instance.

    Returns:
        ClerkAuthAdapter instance (singleton pattern)
    """
    global _clerk_adapter
    if _clerk_adapter is None:
        _clerk_adapter = ClerkAuthAdapter(_get_settings())
    return _clerk_adapter


def _get_user_repository() -> UserRepository:
    """Lazily initialize UserRepository instance.

    Returns:
        UserRepository instance (singleton pattern)
    """
    global _user_repo
    if _user_repo is None:
        _user_repo = UserRepository()
    return _user_repo


clerk_auth_adapter: ClerkAuthAdapter | None = None
user_repository: UserRepository | None = None


def require_auth(f: Callable[..., Any]) -> Callable[..., Any]:
    """Require valid JWT authentication for endpoint access.

    Extracts JWT from Authorization header, validates it via ClerkAuthAdapter,
    retrieves or creates user in database, and injects user into g.current_user.

    Authorization Header Format:
        Authorization: Bearer <jwt_token>

    Authentication Flow:
        1. Extract token from Authorization header
        2. Validate token format (Bearer scheme)
        3. Verify token signature and expiration via ClerkAuthAdapter
        4. Extract clerk_user_id from token payload
        5. Look up user in database via UserRepository
        6. If user doesn't exist, create via User.create_from_clerk()
        7. Inject user into g.current_user

    Args:
        f: Flask endpoint function to protect

    Returns:
        Decorated function that requires authentication

    Raises:
        AuthenticationError: If Authorization header missing, malformed,
            empty, or token validation fails

    Example:
        >>> @app.route("/profile")
        >>> @require_auth
        >>> def profile():
        ...     user = g.current_user
        ...     return {"email": user.email, "role": user.role.value}
    """

    @wraps(f)
    def decorated(*args: Any, **kwargs: Any) -> Any:
        clerk_adapter = clerk_auth_adapter or _get_clerk_adapter()
        user_repo = user_repository or _get_user_repository()

        auth_header = request.headers.get("Authorization")

        if not auth_header:
            raise AuthenticationError("Missing authorization header")

        parts = auth_header.split()

        if len(parts) == 0 or parts[0] != "Bearer":
            raise AuthenticationError("Invalid authorization header format")

        if len(parts) != 2:
            raise AuthenticationError("Empty token")

        token = parts[1].strip()
        if not token:
            raise AuthenticationError("Empty token")

        try:
            payload = clerk_adapter.verify_token(token)
        except ValueError as e:
            raise AuthenticationError(f"Invalid token: {str(e)}") from e

        clerk_user_id = payload["sub"]
        email = payload["email"]

        user = user_repo.find_by_clerk_user_id(clerk_user_id)

        if user is None:
            user = User.create_from_clerk(
                clerk_user_id=clerk_user_id, email=email
            )
            user = user_repo.add(user)

        g.current_user = user

        return f(*args, **kwargs)

    return decorated


def optional_auth(f: Callable[..., Any]) -> Callable[..., Any]:
    """Optionally authenticate the request if a Bearer token is present.

    Attempts JWT validation and user lookup when an Authorization header
    exists. On success, injects the user into ``g.current_user``. On any
    failure (missing header, invalid token, unknown user), proceeds without
    setting ``g.current_user`` so public endpoints remain accessible.

    Use this on public endpoints that serve richer data to authenticated
    callers (e.g. admins see deleted comments).

    Args:
        f: Flask endpoint function to decorate.

    Returns:
        Decorated function that optionally sets ``g.current_user``.

    Example:
        >>> @app.route("/posts/<slug>/comments")
        >>> @optional_auth
        >>> def list_comments(slug: str):
        ...     is_admin = (
        ...         hasattr(g, "current_user")
        ...         and g.current_user.role.can_access_admin_endpoints()
        ...     )
    """

    @wraps(f)
    def decorated(*args: Any, **kwargs: Any) -> Any:
        _try_authenticate_request()
        return f(*args, **kwargs)

    return decorated


def _try_authenticate_request() -> None:
    """Parse Bearer token and set g.current_user when valid.

    Silently no-ops on missing header, malformed tokens, or unknown users.
    """
    auth_header = request.headers.get("Authorization")
    parts = auth_header.split() if auth_header else []
    if len(parts) != 2 or parts[0] != "Bearer" or not parts[1].strip():
        return
    try:
        clerk_adapter = clerk_auth_adapter or _get_clerk_adapter()
        user_repo = user_repository or _get_user_repository()
        payload = clerk_adapter.verify_token(parts[1].strip())
        user = user_repo.find_by_clerk_user_id(payload["sub"])
        if user is not None:
            g.current_user = user
    except Exception:
        logging.getLogger(__name__).warning(
            "Optional authentication failed", exc_info=True
        )


def require_role(
    required_role: str,
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Require specific role for endpoint access.

    Enforces role-based access control by checking if authenticated user
    has required role. Should be composed with @require_auth decorator.

    Role Hierarchy:
        - "authenticated": Any authenticated user (AUTHENTICATED, AUTHOR, ADMIN)
        - "author": AUTHOR or ADMIN roles
        - "admin": ADMIN role only

    Permission Checks:
        - Uses Role.can_access_author_endpoints() for "author" role
        - Uses Role.can_access_admin_endpoints() for "admin" role
        - Allows all authenticated users for "authenticated" role

    Args:
        required_role: Role name ("authenticated", "author", or "admin")

    Returns:
        Decorator function that enforces role-based access control

    Raises:
        AuthenticationError: If user not authenticated (g.current_user missing)
        AuthorizationError: If user lacks required role

    Example:
        >>> @app.route("/posts", methods=["POST"])
        >>> @require_role("author")
        >>> def create_post():
        ...     return {"author": g.current_user.email}

        >>> @app.route("/admin/users")
        >>> @require_role("admin")
        >>> def list_users():
        ...     return {"users": get_all_users()}
    """

    def decorator(f: Callable[..., Any]) -> Callable[..., Any]:
        @wraps(f)
        def decorated(*args: Any, **kwargs: Any) -> Any:
            if not hasattr(g, "current_user"):
                result = f(*args, **kwargs)
                if not hasattr(g, "current_user"):
                    raise AuthenticationError(
                        "User not authenticated. `@require_role` must be used "
                        "with `@require_auth`."
                    )
            else:
                user = g.current_user

                if required_role == "authenticated":
                    return f(*args, **kwargs)

                if required_role == "author":
                    if not user.role.can_access_author_endpoints():
                        raise AuthorizationError(
                            "Author role required", required_role="author"
                        )

                elif required_role == "admin":
                    if not user.role.can_access_admin_endpoints():
                        raise AuthorizationError(
                            "Admin role required", required_role="admin"
                        )

                return f(*args, **kwargs)

            user = g.current_user

            if required_role == "authenticated":
                return result

            if required_role == "author":
                if not user.role.can_access_author_endpoints():
                    raise AuthorizationError(
                        "Author role required", required_role="author"
                    )

            elif required_role == "admin":
                if not user.role.can_access_admin_endpoints():
                    raise AuthorizationError(
                        "Admin role required", required_role="admin"
                    )

            return result

        return decorated

    return decorator
