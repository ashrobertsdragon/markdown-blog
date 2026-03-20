"""Notification preferences, admin history, and unsubscribe routes."""

import hmac
import os

from flask import Blueprint, Response, g, jsonify, request

from backend.api.middleware.auth_middleware import require_auth, require_role
from backend.domain.aggregates.notification_preferences import (
    NotificationPreferences,
)
from backend.infrastructure.persistence.notification_repository import (
    NotificationRepository,
)
from backend.infrastructure.persistence.user_notification_preferences_repository import (  # noqa: E501
    UserNotificationPreferencesRepository,
)
from backend.infrastructure.persistence.user_repository import UserRepository

notifications_bp = Blueprint("notifications", __name__)

_KNOWN_PREF_FIELDS = frozenset(
    {"notify_on_comment_replies", "notify_on_mentions", "notify_on_new_posts"}
)


def _get_preferences_repository() -> UserNotificationPreferencesRepository:
    """Return a UserNotificationPreferencesRepository instance."""
    return UserNotificationPreferencesRepository()


def _get_notification_repository() -> NotificationRepository:
    """Return a NotificationRepository instance."""
    return NotificationRepository()


def _get_user_repository() -> UserRepository:
    """Return a UserRepository instance."""
    return UserRepository()


def _serialize_preferences(prefs: NotificationPreferences) -> dict[str, object]:
    """Convert NotificationPreferences to a JSON-serialisable dict."""
    return {
        "user_id": prefs.user_id,
        "notify_on_comment_replies": prefs.notify_on_comment_replies,
        "notify_on_mentions": prefs.notify_on_mentions,
        "notify_on_new_posts": prefs.notify_on_new_posts,
    }


def _verify_unsubscribe_token(token: str, user_id: int) -> bool:
    """Return True if token is the valid HMAC-SHA256 digest for user_id.

    Uses constant-time comparison to prevent timing attacks.

    Args:
        token: Hex-encoded HMAC-SHA256 digest supplied by the caller.
        user_id: User primary key the token must have been generated for.

    Returns:
        True when the token matches the expected digest, False otherwise.

    Raises:
        RuntimeError: If UNSUBSCRIBE_SECRET environment variable is not set.
    """
    secret = os.environ.get("UNSUBSCRIBE_SECRET")
    if not secret:
        raise RuntimeError(
            "UNSUBSCRIBE_SECRET environment variable is required but not set"
        )
    expected = hmac.new(
        secret.encode(), f"{user_id}".encode(), "sha256"
    ).hexdigest()
    return hmac.compare_digest(token, expected)


@notifications_bp.route("/user/notification-preferences", methods=["GET"])
@require_auth
def get_user_notification_preferences() -> tuple[Response, int]:
    """Return the authenticated user's notification preferences.

    Auto-creates default preferences (all enabled) on first access.

    Returns:
        Tuple of (JSON response with preferences, 200).

    Raises:
        AuthenticationError: Propagated from @require_auth (401).
    """
    user = g.current_user
    repo = _get_preferences_repository()
    prefs = repo.get_preferences(user.id)
    return jsonify({"preferences": _serialize_preferences(prefs)}), 200


@notifications_bp.route("/user/notification-preferences", methods=["PUT"])
@require_auth
def update_user_notification_preferences() -> tuple[Response, int]:
    """Update the authenticated user's notification preferences.

    Accepts partial updates — only provided fields are modified.

    Request body (all fields optional):
        {
            "notify_on_comment_replies": bool,
            "notify_on_mentions": bool,
            "notify_on_new_posts": bool
        }

    Returns:
        Tuple of (JSON response with updated preferences, 200).

    Raises:
        AuthenticationError: Propagated from @require_auth (401).
    """
    body = request.get_json(silent=True)
    if body is None:
        return jsonify({"error": "Request body is required"}), 400
    if not body:
        return jsonify(
            {"error": "At least one preference field is required"}
        ), 400

    for key, value in body.items():
        if key not in _KNOWN_PREF_FIELDS:
            return jsonify({"error": f"Unknown preference field: {key}"}), 400
        if not isinstance(value, bool):
            return (
                jsonify({"error": f"Field '{key}' must be a boolean"}),
                400,
            )

    user = g.current_user
    repo = _get_preferences_repository()
    prefs = repo.get_preferences(user.id)

    if "notify_on_comment_replies" in body:
        prefs.notify_on_comment_replies = body["notify_on_comment_replies"]
    if "notify_on_mentions" in body:
        prefs.notify_on_mentions = body["notify_on_mentions"]
    if "notify_on_new_posts" in body:
        prefs.notify_on_new_posts = body["notify_on_new_posts"]

    repo.update_preferences(user.id, prefs)
    return jsonify({"preferences": _serialize_preferences(prefs)}), 200


@notifications_bp.route("/admin/notifications", methods=["GET"])
@require_auth
@require_role("admin")
def list_notifications_admin() -> tuple[Response, int]:
    """List all notifications for admin monitoring (newest-first).

    Args (query params):
        skip: Number of records to skip (default 0, min 0).
        limit: Max records to return (default 50, max 200).

    Returns:
        Tuple of (JSON response with paginated notifications, 200).
        Note: ``total`` is fetched in a separate query from the page data
        and may differ by rows inserted or deleted between the two calls.
        This is acceptable for an admin monitoring view.

    Raises:
        AuthenticationError: Propagated from @require_auth (401).
        AuthorizationError: Propagated from @require_role (403).
    """
    skip = request.args.get("skip", 0, type=int)
    limit = request.args.get("limit", 50, type=int)

    if skip < 0:
        return jsonify({"error": "skip must be non-negative"}), 400
    if limit < 1 or limit > 200:
        return jsonify({"error": "limit must be between 1 and 200"}), 400

    repo = _get_notification_repository()
    notifications = repo.list_all_admin(skip=skip, limit=limit)
    total = repo.count_all()

    return (
        jsonify(
            {
                "notifications": [n.to_dict() for n in notifications],
                "skip": skip,
                "limit": limit,
                "total": total,
            }
        ),
        200,
    )


@notifications_bp.route("/unsubscribe", methods=["GET"])
def unsubscribe_all() -> tuple[Response, int]:
    """Unsubscribe a user from all notifications via a secure token link.

    This endpoint is unauthenticated. The token replaces authentication by
    proving the caller possesses the shared secret used to generate the link.

    Args (query params):
        user_id: Primary key of the user to unsubscribe.
        token: SHA-256 hex digest generated from user_id and UNSUBSCRIBE_SECRET.

    Returns:
        Tuple of (JSON success message, 200).

    Raises:
        400: Missing parameters, invalid/tampered token, or user not found.
    """
    user_id = request.args.get("user_id", type=int)
    token = request.args.get("token", type=str)

    if user_id is None:
        return jsonify({"error": "Missing required parameter: user_id"}), 400
    if not token:
        return jsonify({"error": "Missing required parameter: token"}), 400

    if not _verify_unsubscribe_token(token, user_id):
        return jsonify({"error": "Invalid or expired unsubscribe token"}), 400

    user_repo = _get_user_repository()
    user = user_repo.find_by_id(user_id)
    if user is None:
        return jsonify({"error": "Invalid unsubscribe request"}), 400

    prefs_repo = _get_preferences_repository()
    prefs_repo.disable_all(user_id)

    return (
        jsonify(
            {
                "message": "Successfully unsubscribed from all notifications",
                "user_id": user_id,
            }
        ),
        200,
    )
