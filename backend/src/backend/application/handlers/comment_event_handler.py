"""Application-layer handlers for comment domain events.

These functions are fire-and-forget: they delegate to the notification
infrastructure, catch all exceptions, and log errors without re-raising.
This keeps the HTTP request path unaffected by notification failures.
"""

import logging

from backend.domain.aggregates.comment import Comment
from backend.domain.events.comment_posted import CommentPostedEvent
from backend.domain.events.reply_received import ReplyReceivedEvent
from backend.infrastructure.notification.comment_notification_handler import (
    CommentNotificationHandler,
)

logger = logging.getLogger(__name__)


def notify_comment_posted(
    comment: Comment,
    post_author_id: int,
    sender_id: int,
    handler: CommentNotificationHandler,
) -> None:
    """Queue a notification when a new top-level comment is posted.

    No notification is queued when the commenter is the post author, as
    authors do not need to be notified of their own comments.

    Args:
        comment: The persisted Comment aggregate that was just created.
        post_author_id: User ID of the post author who should be notified.
        sender_id: User ID of the commenter.
        handler: CommentNotificationHandler used to persist the record.
    """
    if sender_id == post_author_id:
        return

    if comment.id is None:
        raise ValueError("comment.id must be set before queuing a notification")
    event = CommentPostedEvent(
        comment_id=comment.id,
        post_id=comment.post_id,
        sender_id=sender_id,
        recipient_id=post_author_id,
    )

    try:
        handler.queue_comment_posted(event)
    except Exception as exc:
        logger.error("Failed to queue comment_posted notification: %s", exc)


def notify_reply_received(
    comment: Comment,
    parent_author_id: int,
    sender_id: int,
    handler: CommentNotificationHandler,
) -> None:
    """Queue a notification when a reply is posted to an existing comment.

    No notification is queued when the replier is the parent comment author,
    as users do not need to be notified of their own replies.

    Args:
        comment: The persisted reply Comment aggregate that was just created.
        parent_author_id: User ID of the parent comment author to notify.
        sender_id: User ID of the replier.
        handler: CommentNotificationHandler used to persist the record.
    """
    if sender_id == parent_author_id:
        return

    if comment.id is None:
        raise ValueError("comment.id must be set before queuing a notification")
    event = ReplyReceivedEvent(
        comment_id=comment.id,
        post_id=comment.post_id,
        sender_id=sender_id,
        recipient_id=parent_author_id,
    )

    try:
        handler.queue_reply_received(event)
    except Exception as exc:
        logger.error("Failed to queue reply_received notification: %s", exc)
