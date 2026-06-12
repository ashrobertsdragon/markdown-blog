"""Admin-only API routes for system management and moderation."""

import logging
import math
import time

from flask import Blueprint, Response, g, jsonify, request

from ...api.dependencies import get_github_service as _get_github_service
from ...application.commands.handlers.unpublish_post_handler import (
    unpublish_post_handler,
)
from ...application.commands.unpublish_post_command import UnpublishPostCommand
from ...application.queries.get_system_health_query import (
    GetSystemHealthQuery,
    SystemHealth,
)
from ...application.queries.get_user_activity_query import (
    GetUserActivityQuery,
    UserActivity,
)
from ...application.queries.handlers.get_system_health_query_handler import (
    get_system_health_query_handler,
)
from ...application.queries.handlers.get_user_activity_query_handler import (
    get_user_activity_query_handler,
)
from ...config import FileSystemSettings
from ...domain.aggregates.post import Post
from ...domain.value_objects.role import Role
from ...exceptions import NotFoundError
from ...infrastructure.monitoring.error_logger import ErrorLogger
from ...infrastructure.persistence.comment_repository import CommentRepository
from ...infrastructure.persistence.database import get_engine
from ...infrastructure.persistence.filesystem_draft_repository import (
    FileSystemDraftRepository,
)
from ...infrastructure.persistence.post_repository import PostRepository
from ...infrastructure.persistence.user_repository import UserRepository
from ..middleware.auth_middleware import require_auth, require_role

logger = logging.getLogger(__name__)
admin_bp = Blueprint("admin", __name__, url_prefix="/api/admin")
_app_start_time: float = time.time()

_post_repository: PostRepository | None = None
_comment_repository: CommentRepository | None = None
_user_repository: UserRepository | None = None
_draft_repository: FileSystemDraftRepository | None = None
_filesystem_settings: FileSystemSettings | None = None


def _get_post_repository() -> PostRepository:
    """Lazily initialize PostRepository instance."""
    global _post_repository
    if _post_repository is None:
        _post_repository = PostRepository()
    return _post_repository


def _get_comment_repository() -> CommentRepository:
    """Lazily initialize CommentRepository instance."""
    global _comment_repository
    if _comment_repository is None:
        _comment_repository = CommentRepository()
    return _comment_repository


def _get_user_repository() -> UserRepository:
    """Lazily initialize UserRepository instance."""
    global _user_repository
    if _user_repository is None:
        _user_repository = UserRepository()
    return _user_repository


def _get_filesystem_settings() -> FileSystemSettings:
    """Lazily initialize FileSystemSettings instance."""
    global _filesystem_settings
    if _filesystem_settings is None:
        _filesystem_settings = FileSystemSettings()
    return _filesystem_settings


def _get_draft_repository() -> FileSystemDraftRepository:
    """Get FileSystemDraftRepository instance."""
    global _draft_repository
    if _draft_repository is None:
        fs_settings = _get_filesystem_settings()
        _draft_repository = FileSystemDraftRepository(fs_settings.DRAFTS_PATH)
    return _draft_repository


class UnpublishPostHandler:
    """Handler wrapper for unpublish_post_handler."""

    def handle(self, command: UnpublishPostCommand) -> Post:
        """Handle UnpublishPostCommand."""
        return unpublish_post_handler(
            command,
            _get_draft_repository(),
            _get_post_repository(),
            _get_github_service(),
        )


class GetUserActivityHandler:
    """Handler wrapper for get_user_activity_query_handler."""

    def handle(self, query: GetUserActivityQuery) -> UserActivity:
        """Handle GetUserActivityQuery."""
        return get_user_activity_query_handler(
            query,
            _get_user_repository(),
            _get_post_repository(),
            _get_comment_repository(),
        )


class GetSystemHealthHandler:
    """Handler wrapper for get_system_health_query_handler."""

    def handle(self, query: GetSystemHealthQuery) -> SystemHealth:
        """Handle GetSystemHealthQuery."""
        return get_system_health_query_handler(
            query,
            get_engine(),
            _app_start_time,
        )


def _get_unpublish_post_handler() -> UnpublishPostHandler:
    """Get unpublish post handler."""
    return UnpublishPostHandler()


def _get_user_activity_handler() -> GetUserActivityHandler:
    """Get user activity handler."""
    return GetUserActivityHandler()


def _get_system_health_handler() -> GetSystemHealthHandler:
    """Get system health handler."""
    return GetSystemHealthHandler()


def _pagination_params() -> tuple[int, int, int]:
    """Extract and validate page/limit query params.

    Returns:
        Tuple of (page, limit, offset) with page ≥ 1 and limit in [1, 100].
    """
    page = max(1, request.args.get("page", 1, type=int) or 1)
    limit = max(1, min(request.args.get("limit", 10, type=int) or 10, 100))
    return page, limit, (page - 1) * limit


@admin_bp.route("/users", methods=["GET"])
@require_auth
@require_role("admin")
def list_users() -> tuple[Response, int]:
    """List all users with pagination (admin only).

    Query params:
        page: 1-indexed page number (default 1).
        limit: Results per page (default 10, max 100).

    Returns:
        JSON with users array, total_count, total_pages, page, limit.
    """
    page, limit, offset = _pagination_params()
    user_repo = _get_user_repository()
    users = user_repo.list_all(limit=limit, offset=offset)
    total_count = user_repo.count_all()
    total_pages = max(1, math.ceil(total_count / limit))

    return (
        jsonify(
            {
                "users": [
                    {
                        "id": u.id,
                        "email": u.email,
                        "display_name": u.email,
                        "role": u.role.value,
                        "created_at": u.created_at.isoformat(),
                        "last_login": None,
                    }
                    for u in users
                ],
                "total_count": total_count,
                "total_pages": total_pages,
                "page": page,
                "limit": limit,
            }
        ),
        200,
    )


@admin_bp.route("/users/<int:user_id>", methods=["GET"])
@require_auth
@require_role("admin")
def get_user(user_id: int) -> tuple[Response, int]:
    """Return a single user record by ID (admin only).

    Returns:
        JSON with user fields on success, 404 if not found.
    """
    user_repo = _get_user_repository()
    user = user_repo.find_by_id(user_id)
    if user is None:
        return jsonify({"error": "User not found"}), 404

    return (
        jsonify(
            {
                "id": user.id,
                "email": user.email,
                "display_name": user.email,
                "role": user.role.value,
                "created_at": user.created_at.isoformat(),
                "last_login": None,
            }
        ),
        200,
    )


@admin_bp.route("/users/<int:user_id>/role", methods=["PUT"])
@require_auth
@require_role("admin")
def update_user_role(user_id: int) -> tuple[Response, int]:
    """Update the role of a user (admin only).

    Request body:
        role: New role value — "admin" or "authenticated".

    Returns:
        JSON with updated user record on success.

    Raises:
        400: Missing or malformed body.
        404: User not found.
        422: Invalid role value.
    """
    body = request.get_json(silent=True)
    if not body or "role" not in body:
        return jsonify({"error": "Field 'role' is required"}), 400

    new_role = body.get("role")
    valid_roles = {"admin", "authenticated"}
    if new_role not in valid_roles:
        return (
            jsonify(
                {"error": f"Invalid role: must be one of {sorted(valid_roles)}"}
            ),
            422,
        )

    user_repo = _get_user_repository()
    user = user_repo.find_by_id(user_id)
    if user is None:
        return jsonify({"error": "User not found"}), 404

    user.role = Role(new_role)
    updated = user_repo.save(user)

    return (
        jsonify(
            {
                "id": updated.id,
                "email": updated.email,
                "display_name": updated.email,
                "role": updated.role.value,
                "created_at": updated.created_at.isoformat(),
                "last_login": None,
            }
        ),
        200,
    )


@admin_bp.route("/posts/<int:post_id>/unpublish", methods=["POST"])
@require_auth
@require_role("admin")
def unpublish_post(post_id: int) -> tuple[Response, int]:
    """Unpublish a post (admin only)."""
    try:
        command = UnpublishPostCommand(
            post_id=post_id,
            author_id=g.current_user.id,
            user_role=g.current_user.role.value,
        )
        handler = _get_unpublish_post_handler()
        handler.handle(command)
        return jsonify({"message": "Post unpublished"}), 200
    except NotFoundError as e:
        return jsonify({"error": str(e)}), 404
    except ValueError as e:
        return jsonify({"error": str(e)}), 400


@admin_bp.route("/posts", methods=["GET"])
@require_auth
@require_role("admin")
def list_posts() -> tuple[Response, int]:
    """List all published posts with pagination (admin only).

    Query params:
        page: 1-indexed page number (default 1).
        limit: Results per page (default 10, max 100).

    Returns:
        JSON with posts array, total_count, total_pages, page, limit.
    """
    page, limit, offset = _pagination_params()
    post_repo = _get_post_repository()
    posts = post_repo.list_published(limit=limit, offset=offset)
    total_count = post_repo.count_published()
    total_pages = max(1, math.ceil(total_count / limit))

    user_repo = _get_user_repository()
    author_ids = {p.author_id for p in posts if p.author_id is not None}
    author_map = {
        aid: u.email
        for aid in author_ids
        if (u := user_repo.find_by_id(aid)) is not None
    }

    return (
        jsonify(
            {
                "posts": [
                    {
                        "id": p.id,
                        "slug": str(p.slug),
                        "title": p.title,
                        "author": author_map.get(p.author_id, "")
                        if p.author_id
                        else "",
                        "author_id": p.author_id or 0,
                        "published_at": p.published_at.isoformat()
                        if p.published_at
                        else "",
                        "created_at": p.created_at.isoformat()
                        if p.created_at
                        else "",
                    }
                    for p in posts
                ],
                "total_count": total_count,
                "total_pages": total_pages,
                "page": page,
                "limit": limit,
            }
        ),
        200,
    )


@admin_bp.route("/comments", methods=["GET"])
@require_auth
@require_role("admin")
def list_comments() -> tuple[Response, int]:
    """List all comments across all posts with pagination (admin only).

    Query params:
        page: 1-indexed page number (default 1).
        limit: Results per page (default 10, max 100).

    Returns:
        JSON with comments array, total_count, total_pages, page, limit.
    """
    page, limit, offset = _pagination_params()
    comment_repo = _get_comment_repository()
    comments = comment_repo.list_all_admin(limit=limit, offset=offset)
    total_count = comment_repo.count_all_admin()
    total_pages = max(1, math.ceil(total_count / limit))

    user_repo = _get_user_repository()
    post_repo = _get_post_repository()

    author_ids = {c.author_id for c in comments if c.author_id is not None}
    author_map = {
        aid: u.email
        for aid in author_ids
        if (u := user_repo.find_by_id(aid)) is not None
    }

    post_ids = {c.post_id for c in comments}
    post_map = {
        pid: p.title
        for pid in post_ids
        if (p := post_repo.find_by_id(pid)) is not None
    }

    return (
        jsonify(
            {
                "comments": [
                    {
                        "id": c.id,
                        "text": str(c.text),
                        "author": author_map.get(c.author_id, "")
                        if c.author_id
                        else "",
                        "author_id": c.author_id or 0,
                        "post_title": post_map.get(c.post_id, ""),
                        "post_id": c.post_id,
                        "created_at": c.created_at.isoformat()
                        if c.created_at
                        else "",
                    }
                    for c in comments
                ],
                "total_count": total_count,
                "total_pages": total_pages,
                "page": page,
                "limit": limit,
            }
        ),
        200,
    )


@admin_bp.route("/comments/<int:comment_id>", methods=["DELETE"])
@require_auth
@require_role("admin")
def delete_comment(comment_id: int) -> tuple[Response, int]:
    """Permanently delete a comment (admin only).

    Returns:
        204 No Content on success, 404 if not found.
    """
    comment_repo = _get_comment_repository()
    deleted = comment_repo.soft_delete(comment_id)
    if not deleted:
        return jsonify({"error": f"Comment {comment_id} not found"}), 404
    return jsonify({}), 204


@admin_bp.route("/users/<int:user_id>/activity", methods=["GET"])
@require_auth
@require_role("admin")
def get_user_activity(user_id: int) -> tuple[Response, int]:
    """Get user activity summary (admin only)."""
    try:
        query = GetUserActivityQuery(user_id=user_id)
        handler = _get_user_activity_handler()
        activity = handler.handle(query)
        return (
            jsonify(
                {
                    "user_id": user_id,
                    "last_login": activity.last_login.isoformat()
                    if activity.last_login
                    else None,
                    "posts_count": activity.posts_count,
                    "comments_count": activity.comments_count,
                    "recent_posts": [
                        p.to_dict() for p in activity.recent_posts
                    ],
                    "recent_comments": [
                        c.to_dict() for c in activity.recent_comments
                    ],
                }
            ),
            200,
        )
    except NotFoundError as e:
        return jsonify({"error": str(e)}), 404
    except ValueError as e:
        return jsonify({"error": str(e)}), 400


@admin_bp.route("/system/health", methods=["GET"])
@require_auth
@require_role("admin")
def get_system_health() -> tuple[Response, int]:
    """Get system health metrics (admin only)."""
    query = GetSystemHealthQuery()
    handler = _get_system_health_handler()
    health = handler.handle(query)
    return (
        jsonify(
            {
                "status": health.status,
                "database": health.database,
                "filesystem": health.filesystem,
                "github_api": health.github_api,
                "uptime_seconds": health.uptime_seconds,
                "checked_at": health.checked_at,
            }
        ),
        200,
    )


@admin_bp.route("/system/errors", methods=["GET"])
@require_auth
@require_role("admin")
def get_error_logs() -> tuple[Response, int]:
    """Get recent error logs (admin only)."""
    limit = max(1, min(request.args.get("limit", 50, type=int) or 50, 100))
    errors = ErrorLogger.get_recent_errors(limit=limit)
    return (
        jsonify(
            {
                "errors": [
                    {
                        "id": i + 1,
                        "level": "error",
                        "message": e.message,
                        "timestamp": e.timestamp.isoformat(),
                        "context": {
                            "stack_trace": e.stack_trace,
                            "endpoint": e.endpoint,
                        },
                    }
                    for i, e in enumerate(errors)
                ],
                "total_count": len(errors),
                "limit": limit,
            }
        ),
        200,
    )
