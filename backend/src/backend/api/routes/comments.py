"""Comments API routes for comment and admin moderation operations."""

import logging

from flask import Blueprint, Response, g, jsonify, request

from backend.api.middleware.auth_middleware import require_auth, require_role
from backend.application.commands.delete_comment_command import (
    DeleteCommentCommand,
)
from backend.application.commands.handlers.delete_comment_handler import (
    handle_delete_comment,
)
from backend.application.commands.handlers.moderate_comment_handler import (
    handle_moderate_comment,
)
from backend.application.commands.handlers.post_comment_handler import (
    handle_post_comment,
)
from backend.application.commands.handlers.reply_to_comment_handler import (
    handle_reply_to_comment,
)
from backend.application.commands.moderate_comment_command import (
    ModerateCommentCommand,
)
from backend.application.commands.post_comment_command import PostCommentCommand
from backend.application.commands.reply_to_comment_command import (
    ReplyToCommentCommand,
)
from backend.application.queries.get_post_comments_query import (
    GetPostCommentsQuery,
)
from backend.application.queries.handlers import (
    handle_get_post_comments,
)
from backend.infrastructure.moderation.rate_limit_service import (
    RateLimitService,
)
from backend.infrastructure.moderation.spam_check_service import (
    SpamCheckService,
)
from backend.infrastructure.persistence.comment_repository import (
    CommentRepository,
)
from backend.infrastructure.persistence.post_repository import PostRepository

comments_bp = Blueprint("comments", __name__)
admin_comments_bp = Blueprint("admin_comments", __name__)
logger = logging.getLogger(__name__)

_post_repository: PostRepository | None = None
_comment_repository: CommentRepository | None = None
_rate_limit_service: RateLimitService | None = None
_spam_check_service: SpamCheckService | None = None


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


def _get_rate_limit_service() -> RateLimitService:
    """Lazily initialize RateLimitService instance."""
    global _rate_limit_service
    if _rate_limit_service is None:
        _rate_limit_service = RateLimitService()
    return _rate_limit_service


def _get_spam_check_service() -> SpamCheckService:
    """Lazily initialize SpamCheckService instance."""
    global _spam_check_service
    if _spam_check_service is None:
        _spam_check_service = SpamCheckService()
    return _spam_check_service


@comments_bp.route("/<slug>/comments", methods=["GET"])
def list_comments(slug: str) -> tuple[Response, int]:
    """List published comments for a post with pagination.

    Public endpoint — no authentication required. Admins see pending and
    deleted comments; anonymous callers see only published ones.

    Args:
        slug: Post slug identifier.

    Returns:
        JSON with comments array, total_count, and has_more flag with 200.

    Raises:
        404: Post not found.
    """
    post = _get_post_repository().find_by_slug(slug)
    if post is None:
        return jsonify({"error": "Post not found"}), 404

    try:
        skip = int(request.args.get("skip", 0))
        limit = int(request.args.get("limit", 50))
    except ValueError:
        return jsonify({"error": "skip and limit must be integers"}), 400

    if skip < 0:
        return jsonify({"error": "skip must be 0 or greater"}), 400
    if not 1 <= limit <= 100:
        return jsonify({"error": "limit must be between 1 and 100"}), 400

    is_admin = (
        hasattr(g, "current_user")
        and g.current_user.role.can_access_admin_endpoints()
    )

    assert post.id is not None
    query = GetPostCommentsQuery(
        post_id=post.id,
        skip=skip,
        limit=limit,
        show_pending=is_admin,
    )
    result = handle_get_post_comments(query, _get_comment_repository())

    return jsonify(
        {
            "comments": [c.to_dict() for c in result.comments],
            "total_count": result.total_count,
            "has_more": result.has_more,
        }
    ), 200


@comments_bp.route("/<slug>/comments", methods=["POST"])
@require_auth
def post_comment(slug: str) -> tuple[Response, int]:
    """Post a new comment on a published blog post.

    Rate-limited to 5 per minute per user; bypassed for admins. Spam
    detection may flag the comment for moderation without blocking it.

    Args:
        slug: Post slug identifier.

    Returns:
        JSON with the created comment and 201 status.

    Raises:
        400: Missing or invalid text field.
        401: Missing or invalid authentication.
        404: Post not found.
        429: Rate limit exceeded.
    """
    post = _get_post_repository().find_by_slug(slug)
    if post is None:
        return jsonify({"error": "Post not found"}), 404

    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "Request body must be JSON"}), 400

    text = data.get("text", "")
    if not text or not str(text).strip():
        return jsonify({"error": "Missing required field: text"}), 400

    assert post.id is not None
    assert g.current_user.id is not None
    command = PostCommentCommand(
        post_id=post.id,
        author_id=g.current_user.id,
        text=str(text),
        ip_address=request.remote_addr or "unknown",
        is_admin=g.current_user.role.can_access_admin_endpoints(),
    )

    try:
        comment = handle_post_comment(
            command,
            _get_rate_limit_service(),
            _get_spam_check_service(),
        )
    except ValueError as e:
        return jsonify({"error": str(e)}), 400

    saved = _get_comment_repository().save(comment)
    return jsonify(saved.to_dict()), 201


@comments_bp.route("/<slug>/comments/<int:comment_id>/reply", methods=["POST"])
@require_auth
def post_reply(slug: str, comment_id: int) -> tuple[Response, int]:
    """Post a reply to an existing comment.

    Verifies parent comment belongs to the given post before creating.
    Subject to the same rate limiting and spam detection as top-level comments.

    Args:
        slug: Post slug identifier.
        comment_id: Parent comment ID.

    Returns:
        JSON with the created reply and 201 status.

    Raises:
        400: Missing or invalid text field.
        401: Missing or invalid authentication.
        404: Post or parent comment not found.
        429: Rate limit exceeded.
    """
    post = _get_post_repository().find_by_slug(slug)
    if post is None:
        return jsonify({"error": "Post not found"}), 404

    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "Request body must be JSON"}), 400

    text = data.get("text", "")
    if not text or not str(text).strip():
        return jsonify({"error": "Missing required field: text"}), 400

    assert post.id is not None
    assert g.current_user.id is not None
    command = ReplyToCommentCommand(
        post_id=post.id,
        parent_comment_id=comment_id,
        author_id=g.current_user.id,
        text=str(text),
        ip_address=request.remote_addr or "unknown",
        is_admin=g.current_user.role.can_access_admin_endpoints(),
    )

    try:
        comment = handle_reply_to_comment(
            command,
            _get_rate_limit_service(),
            _get_spam_check_service(),
            _get_comment_repository(),
        )
    except ValueError as e:
        error_msg = str(e).lower()
        if "not found" in error_msg:
            return jsonify({"error": str(e)}), 404
        return jsonify({"error": str(e)}), 400

    saved = _get_comment_repository().save(comment)
    return jsonify(saved.to_dict()), 201


@comments_bp.route("/<slug>/comments/<int:comment_id>", methods=["DELETE"])
@require_auth
def delete_comment(slug: str, comment_id: int) -> tuple[Response, int]:
    """Delete a comment.

    Authors hard-delete their own comments; admins and post authors
    soft-delete any comment. Authorization is enforced in the handler.

    Args:
        slug: Post slug identifier.
        comment_id: Comment ID to delete.

    Returns:
        Empty 204 response on success.

    Raises:
        401: Missing or invalid authentication.
        403: User not authorised to delete this comment.
        404: Post or comment not found.
    """
    post = _get_post_repository().find_by_slug(slug)
    if post is None:
        return jsonify({"error": "Post not found"}), 404

    assert g.current_user.id is not None
    command = DeleteCommentCommand(
        comment_id=comment_id,
        author_id=g.current_user.id,
        user_role=g.current_user.role.value,
    )

    try:
        handle_delete_comment(command, _get_comment_repository())
    except ValueError as e:
        error_msg = str(e).lower()
        if "not found" in error_msg:
            return jsonify({"error": str(e)}), 404
        if "another user" in error_msg:
            return jsonify({"error": str(e)}), 403
        return jsonify({"error": str(e)}), 400

    return Response("", status=204), 204


@admin_comments_bp.route("/comments/<int:comment_id>/approve", methods=["PUT"])
@require_auth
@require_role("admin")
def approve_comment(comment_id: int) -> tuple[Response, int]:
    """Approve a comment pending moderation.

    Args:
        comment_id: Comment ID to approve.

    Returns:
        JSON with the updated comment and 200 status.

    Raises:
        401: Missing or invalid authentication.
        403: User lacks admin role.
        404: Comment not found.
    """
    assert g.current_user.id is not None
    command = ModerateCommentCommand(
        comment_id=comment_id,
        action="approve",
        moderator_id=g.current_user.id,
        user_role=g.current_user.role.value,
    )

    try:
        comment = handle_moderate_comment(command, _get_comment_repository())
    except ValueError as e:
        error_msg = str(e).lower()
        if "not found" in error_msg:
            return jsonify({"error": str(e)}), 404
        return jsonify({"error": str(e)}), 400

    if comment is None:
        return jsonify({"error": "Comment not found"}), 404

    return jsonify(comment.to_dict()), 200


@admin_comments_bp.route("/comments/<int:comment_id>", methods=["DELETE"])
@require_auth
@require_role("admin")
def admin_delete_comment(comment_id: int) -> tuple[Response, int]:
    """Soft-delete a comment as admin.

    Replaces comment text with a moderation notice rather than removing
    the row, so reply threads remain coherent.

    Args:
        comment_id: Comment ID to soft-delete.

    Returns:
        Empty 204 response on success.

    Raises:
        401: Missing or invalid authentication.
        403: User lacks admin role.
        404: Comment not found.
    """
    assert g.current_user.id is not None
    command = ModerateCommentCommand(
        comment_id=comment_id,
        action="reject",
        moderator_id=g.current_user.id,
        user_role=g.current_user.role.value,
    )

    try:
        handle_moderate_comment(command, _get_comment_repository())
    except ValueError as e:
        error_msg = str(e).lower()
        if "not found" in error_msg:
            return jsonify({"error": str(e)}), 404
        return jsonify({"error": str(e)}), 400

    return Response("", status=204), 204
