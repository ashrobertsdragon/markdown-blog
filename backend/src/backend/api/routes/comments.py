"""Comments API routes for comment and admin moderation operations."""

import logging

from flask import Blueprint, Response, g, jsonify, request, stream_with_context

from backend.api.middleware.auth_middleware import (
    optional_auth,
    require_auth,
    require_role,
)
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
from backend.application.handlers.comment_event_handler import (
    notify_comment_posted,
    notify_mention,
    notify_reply_received,
)
from backend.application.queries.get_post_comments_query import (
    GetPostCommentsQuery,
)
from backend.application.queries.handlers import (
    handle_get_post_comments,
)
from backend.domain.aggregates.comment import Comment
from backend.domain.aggregates.post import Post
from backend.domain.services.mention_service import extract_mentions
from backend.exceptions import AuthorizationError
from backend.infrastructure.moderation.rate_limit_service import (
    RateLimitService,
)
from backend.infrastructure.moderation.spam_check_service import (
    SpamCheckService,
)
from backend.infrastructure.notification.comment_notification_handler import (
    CommentNotificationHandler,
)
from backend.infrastructure.persistence.comment_repository import (
    CommentRepository,
)
from backend.infrastructure.persistence.post_repository import PostRepository
from backend.infrastructure.persistence.user_notification_preferences_repository import (  # noqa: E501
    UserNotificationPreferencesRepository,
)
from backend.infrastructure.persistence.user_repository import UserRepository
from backend.infrastructure.realtime.comment_stream_service import (
    CommentPayload,
    CommentStreamService,
)

_MAX_MENTIONS_PER_COMMENT = 10

comments_bp = Blueprint("comments", __name__)
admin_comments_bp = Blueprint("admin_comments", __name__)
logger = logging.getLogger(__name__)


def _comment_to_response_dict(comment: Comment, post: Post) -> CommentPayload:
    """Build a public comment response dict with the is_post_author flag.

    Centralizes the pattern used by list_comments, post_comment, and
    post_reply so the logic stays consistent and author_id is never
    included in public API responses.

    Args:
        comment: The comment aggregate to serialize.
        post: The post the comment belongs to, used to compute is_post_author.

    Returns:
        Public comment dict with is_post_author appended.
    """
    assert comment.id is not None
    return CommentPayload(
        id=comment.id,
        post_id=comment.post_id,
        text=str(comment.text),
        parent_id=comment.parent_id,
        created_at=comment.created_at.isoformat(),
        updated_at=comment.updated_at.isoformat(),
        is_deleted=comment.is_deleted,
        is_pending_moderation=comment.is_pending_moderation,
        is_post_author=comment.author_id == post.author_id,
    )


_post_repository: PostRepository | None = None
_comment_repository: CommentRepository | None = None
_rate_limit_service: RateLimitService | None = None
_spam_check_service: SpamCheckService | None = None
_comment_stream_service: CommentStreamService | None = None
_comment_notification_handler: CommentNotificationHandler | None = None
_user_repository: UserRepository | None = None
_notification_preferences_repository: (
    UserNotificationPreferencesRepository | None
) = None


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


def _get_comment_stream_service() -> CommentStreamService:
    """Lazily initialize CommentStreamService instance."""
    global _comment_stream_service
    if _comment_stream_service is None:
        _comment_stream_service = CommentStreamService()
    return _comment_stream_service


def _get_comment_notification_handler() -> CommentNotificationHandler:
    """Lazily initialize CommentNotificationHandler instance."""
    global _comment_notification_handler
    if _comment_notification_handler is None:
        _comment_notification_handler = CommentNotificationHandler()
    return _comment_notification_handler


def _get_user_repository() -> UserRepository:
    """Lazily initialize UserRepository instance."""
    global _user_repository
    if _user_repository is None:
        _user_repository = UserRepository()
    return _user_repository


def _get_notification_preferences_repository() -> (
    UserNotificationPreferencesRepository
):
    """Lazily initialize UserNotificationPreferencesRepository instance."""
    global _notification_preferences_repository
    if _notification_preferences_repository is None:
        _notification_preferences_repository = (
            UserNotificationPreferencesRepository()
        )
    return _notification_preferences_repository


def _dispatch_mention_notifications(comment: Comment, sender_id: int) -> None:
    """Fire mention notifications for each @username in comment text.

    Resolves each mentioned username to a user via email prefix lookup,
    then queues a notification respecting the recipient's preferences.
    Capped at _MAX_MENTIONS_PER_COMMENT to prevent notification flooding.
    Errors are handled inside notify_mention (fire-and-forget); this
    function never raises.

    Args:
        comment: The persisted comment whose text may contain @mentions.
        sender_id: User ID of the comment author.
    """
    mentioned = extract_mentions(str(comment.text))[:_MAX_MENTIONS_PER_COMMENT]
    if not mentioned:
        return
    try:
        user_repo = _get_user_repository()
        handler = _get_comment_notification_handler()
        prefs_repo = _get_notification_preferences_repository()
        for username in mentioned:
            mentioned_user = user_repo.find_by_email_prefix(username)
            if mentioned_user and mentioned_user.id is not None:
                notify_mention(
                    comment=comment,
                    sender_id=sender_id,
                    recipient_id=mentioned_user.id,
                    handler=handler,
                    preferences_repo=prefs_repo,
                )
    except Exception:
        logger.exception("Failed to dispatch mention notifications")


@comments_bp.route("/<slug>/comments", methods=["GET"])
@optional_auth
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
            "comments": [
                _comment_to_response_dict(c, post) for c in result.comments
            ],
            "total_count": result.total_count,
            "has_more": result.has_more,
        }
    ), 200


@comments_bp.route("/<slug>/comments/stream", methods=["GET"])
def stream_comments(slug: str) -> tuple[Response, int] | Response:
    """Stream new comments for a post as Server-Sent Events.

    Public endpoint — no authentication required. Returns a
    ``text/event-stream`` response that yields SSE-formatted strings as
    new comments are published. Clients may pass ``last_comment_id`` to
    resume after a reconnect and receive only comments posted since then.

    Args:
        slug: Post slug identifier.

    Returns:
        Streaming SSE response with mimetype ``text/event-stream``, or a
        404 JSON response if the post does not exist.

    Raises:
        404: Post not found.
    """
    post = _get_post_repository().find_by_slug(slug)
    if post is None:
        return jsonify({"error": "Post not found"}), 404

    raw_last_id = request.args.get("last_comment_id")
    last_comment_id: int | None = None
    if raw_last_id is not None:
        try:
            last_comment_id = int(raw_last_id)
        except ValueError:
            return jsonify({"error": "last_comment_id must be an integer"}), 400

    generator = _get_comment_stream_service().subscribe(
        slug, last_comment_id=last_comment_id
    )

    response = Response(
        stream_with_context(generator),
        mimetype="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
    return response


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
            _get_comment_repository(),
        )
    except ValueError:
        return jsonify({"error": "Post not found"}), 400

    comment_dict = _comment_to_response_dict(comment, post)
    _get_comment_stream_service().publish(slug, comment_dict)

    if post.author_id is not None:
        notify_comment_posted(
            comment=comment,
            post_author_id=post.author_id,
            sender_id=comment.author_id,
            handler=_get_comment_notification_handler(),
        )

    _dispatch_mention_notifications(comment, comment.author_id)

    return jsonify(comment_dict), 201


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
        comment, parent_author_id = handle_reply_to_comment(
            command,
            _get_rate_limit_service(),
            _get_spam_check_service(),
            _get_comment_repository(),
        )
    except ValueError as e:
        if "not found" in str(e).lower():
            return jsonify({"error": "Comment not found"}), 404
        return jsonify({"error": "Resource not found"}), 400

    comment_dict = _comment_to_response_dict(comment, post)
    _get_comment_stream_service().publish(slug, comment_dict)

    if parent_author_id == 0:
        logger.warning(
            "parent_author_id unavailable for reply comment %s;"
            " skipping notification",
            comment.id,
        )
    else:
        notify_reply_received(
            comment=comment,
            parent_author_id=parent_author_id,
            sender_id=comment.author_id,
            handler=_get_comment_notification_handler(),
        )

    _dispatch_mention_notifications(comment, comment.author_id)

    return jsonify(comment_dict), 201


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
        403: User not authorized to delete this comment.
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
    except AuthorizationError:
        return jsonify({"error": "Not authorized"}), 403
    except ValueError as e:
        if "not found" in str(e).lower():
            return jsonify({"error": "Comment not found"}), 404
        return jsonify({"error": "Resource not found"}), 400

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
        if "not found" in str(e).lower():
            return jsonify({"error": "Comment not found"}), 404
        return jsonify({"error": "Resource not found"}), 400

    return jsonify(comment.to_dict()), 200


@admin_comments_bp.route("/comments/<int:comment_id>", methods=["DELETE"])
@require_auth
@require_role("admin")
def admin_delete_comment(comment_id: int) -> tuple[Response, int]:
    """Soft-delete a comment as admin via moderation reject action.

    Marks the comment as deleted without removing the row, preserving
    reply thread coherence.

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
        if "not found" in str(e).lower():
            return jsonify({"error": "Comment not found"}), 404
        return jsonify({"error": "Resource not found"}), 400

    return Response("", status=204), 204
