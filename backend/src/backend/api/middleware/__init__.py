"""Flask middleware components for authentication and authorization.

This module provides decorators for protecting Flask endpoints with
JWT authentication and role-based access control (RBAC).

Available Decorators:
    @require_auth: Validates JWT token and injects current user into g
    @require_role(role): Enforces role-based access control

Usage Examples:
    Simple authentication:
        >>> @app.route("/profile")
        >>> @require_auth
        >>> def profile():
        ...     user = g.current_user
        ...     return {"email": user.email}

    Role-based authorization:
        >>> @app.route("/posts", methods=["POST"])
        >>> @require_role("author")
        >>> def create_post():
        ...     user = g.current_user
        ...     return create_post_for_user(user)

    Admin-only endpoints:
        >>> @app.route("/admin/users")
        >>> @require_role("admin")
        >>> def list_users():
        ...     return get_all_users()
"""

from backend.api.middleware.auth_middleware import require_auth, require_role

__all__ = ["require_auth", "require_role"]
