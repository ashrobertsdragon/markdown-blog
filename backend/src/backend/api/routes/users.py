"""User management routes blueprint for admin operations.

This module provides administrative endpoints for user management including
listing users and updating user roles. All endpoints require admin auth.

Routes:
    GET /: List all users with pagination (admin only)
    PUT /<int:user_id>/role: Update user role (admin only)

Architecture:
    - Uses @require_role('admin') decorator for authorization
    - Reads g.current_user injected by auth middleware
    - Returns JSON responses via jsonify()
    - Implements pagination for list endpoint
    - Validates role enum values

Usage:
    Register blueprint in Flask app:
        >>> from backend.api.routes.users import users_bp
        >>> app.register_blueprint(users_bp, url_prefix="/users")
"""

from flask import Blueprint, Response, jsonify, request

from backend.api.middleware.auth_middleware import require_auth, require_role
from backend.domain.value_objects.role import Role
from backend.infrastructure.persistence.user_repository import UserRepository

users_bp = Blueprint("users", __name__)


def _get_user_repository() -> UserRepository:
    """Get UserRepository instance for dependency injection.

    Returns:
        UserRepository instance for user persistence operations.
    """
    return UserRepository()


@users_bp.route("", methods=["GET"])
@require_auth
@require_role("admin")
def list_users() -> tuple[Response, int]:
    """List all users with pagination (admin only).

    Returns paginated list of users ordered by creation date (newest first).
    Supports limit and offset query parameters for pagination.

    Authentication:
        Requires admin role. @require_role decorator validates JWT and checks
        role before executing endpoint logic.

    Query Parameters:
        limit (int, optional): Maximum users to return. Default: 50, Max: 100
        offset (int, optional): Number of users to skip. Default: 0, Min: 0

    Returns:
        Tuple of (JSON response with users list and pagination metadata, 200)

    Response Format:
        {
            "users": [
                {
                    "id": 1,
                    "clerk_user_id": "user_2abc123",
                    "email": "user@example.com",
                    "role": "authenticated",
                    "created_at": "2025-01-12T10:30:00+00:00"
                },
                ...
            ],
            "limit": 50,
            "offset": 0
        }

    Raises:
        AuthorizationError: If user is not admin (handled by decorator, 403)
        AuthenticationError: If not authenticated (handled by decorator, 401)

    Example:
        >>> curl -H "Authorization: Bearer <admin_token>" \
        >>>      "http://api/users?limit=25&offset=50"
    """
    limit = request.args.get("limit", 50, type=int)
    offset = request.args.get("offset", 0, type=int)

    if limit < 1 or limit > 100:
        return jsonify({"error": "limit must be between 1 and 100"}), 400

    if offset < 0:
        return jsonify({"error": "offset must be non-negative"}), 400

    user_repo = _get_user_repository()
    users = user_repo.list_all(limit=limit, offset=offset)

    return (
        jsonify(
            {
                "users": [user.to_dict() for user in users],
                "limit": limit,
                "offset": offset,
            }
        ),
        200,
    )


@users_bp.route("/<int:user_id>/role", methods=["PUT"])
@require_auth
@require_role("admin")
def update_user_role(user_id: int) -> tuple[Response, int]:
    """Update user role (admin only).

    Changes target user's role to the specified value. Role must be one of:
    authenticated, author, or admin.

    Authentication:
        Requires admin role. @require_role decorator validates JWT and checks
        role before executing endpoint logic.

    Path Parameters:
        user_id (int): Database ID of user to update

    Request Body:
        {
            "role": "author"  // One of: authenticated, author, admin
        }

    Returns:
        Tuple of (JSON response with updated user, 200)

    Response Format:
        {
            "user": {
                "id": 5,
                "clerk_user_id": "user_456",
                "email": "author@example.com",
                "role": "author",
                "created_at": "2025-01-10T12:00:00+00:00"
            }
        }

    Error Responses:
        400: Invalid role value or missing role field
        404: User not found
        403: Not admin (handled by decorator)
        401: Not authenticated (handled by decorator)

    Raises:
        AuthorizationError: If user is not admin (handled by decorator)
        AuthenticationError: If not authenticated (handled by decorator)

    Example:
        >>> curl -X PUT -H "Authorization: Bearer <admin_token>" \
        >>>      -H "Content-Type: application/json" \
        >>>      -d '{"role": "author"}' \
        >>>      "http://api/users/5/role"
    """
    request_data = request.get_json()
    if request_data is None:
        return jsonify({"error": "Request body is required"}), 400

    new_role_str = request_data.get("role")
    if not new_role_str:
        return jsonify({"error": "role field is required"}), 400

    try:
        new_role = Role(new_role_str)
    except ValueError:
        return (
            jsonify(
                {
                    "error": f"Invalid role value: {new_role_str}. "
                    "Must be one of: authenticated, author, admin"
                }
            ),
            400,
        )

    user_repo = _get_user_repository()
    user = user_repo.find_by_id(user_id)
    if not user:
        return jsonify({"error": f"User with id {user_id} not found"}), 404

    user.change_role(new_role)
    updated_user = user_repo.save(user)

    return jsonify({"user": updated_user.to_dict()}), 200
