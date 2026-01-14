"""Authentication routes blueprint for user profile and session management.

This module provides authentication endpoints for retrieving authenticated user
information. All endpoints require JWT authentication via @require_auth.

Routes:
    GET /me: Get current authenticated user's profile

Architecture:
    - Uses @require_auth decorator for JWT validation
    - Reads g.current_user injected by auth middleware
    - Returns JSON responses via jsonify()
    - Error handling delegated to auth middleware

Usage:
    Register blueprint in Flask app:
        >>> from backend.api.routes.auth import auth_bp
        >>> app.register_blueprint(auth_bp, url_prefix="/auth")

    Access authenticated user profile:
        >>> GET /auth/me
        >>> Headers: Authorization: Bearer <jwt_token>
        >>> Response: {"id": 1, "email": "user@example.com", ...}
"""

from flask import Blueprint, Response, g, jsonify

from backend.api.middleware.auth_middleware import require_auth

auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/me", methods=["GET"])
@require_auth
def get_current_user() -> tuple[Response, int]:
    """Get current authenticated user's profile.

    Requires valid JWT authentication. Returns user profile data including
    id, clerk_user_id, email, role, and created_at timestamp.

    Authentication:
        Requires Authorization header with Bearer token.
        @require_auth decorator validates JWT and injects g.current_user.

    Returns:
        Tuple of (JSON response with user profile, 200 status code)

    Response Format:
        {
            "id": 1,
            "clerk_user_id": "user_2abc123",
            "email": "user@example.com",
            "role": "authenticated",
            "created_at": "2025-01-12T10:30:00.123456+00:00"
        }

    Raises:
        AuthenticationError: If Authorization header missing, malformed,
            or token invalid (handled by @require_auth decorator)

    Example:
        >>> curl -H "Authorization: Bearer <token>" http://api/auth/me
        >>> {"id": 1, "email": "user@example.com", "role": "authenticated"}
    """
    user = g.current_user
    return jsonify(user.to_dict()), 200
