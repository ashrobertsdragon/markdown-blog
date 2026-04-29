"""Admin-only API routes for system management and moderation."""

import logging
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


@admin_bp.route("/posts/<int:post_id>/unpublish", methods=["POST"])
@require_auth
@require_role("admin")
def unpublish_post(post_id: int) -> tuple[Response, int]:
    """Unpublish a post (admin only)."""
    try:
        post = _get_post_repository().find_by_id(post_id)
        if post is None:
            return jsonify({"error": "Post not found"}), 404

        command = UnpublishPostCommand(
            slug=post.slug.value,
            author_id=g.current_user.id,
            user_role=g.current_user.role.value,
        )
        handler = _get_unpublish_post_handler()
        handler.handle(command)
        return jsonify({"message": "Post unpublished"}), 200
    except ValueError as e:
        error_msg = str(e).lower()
        if "not found" in error_msg:
            return jsonify({"error": "Post not found"}), 404
        return jsonify({"error": str(e)}), 400


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
                    "recent_posts": [],
                    "recent_comments": [],
                }
            ),
            200,
        )
    except ValueError as e:
        error_msg = str(e).lower()
        if "not found" in error_msg:
            return jsonify({"error": "User not found"}), 404
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
                "api_status": health.api_status,
                "database_status": health.database_status,
                "uptime": health.uptime,
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
                        "timestamp": e.timestamp.isoformat(),
                        "message": e.message,
                        "stack_trace": e.stack_trace,
                        "endpoint": e.endpoint,
                    }
                    for e in errors
                ]
            }
        ),
        200,
    )
