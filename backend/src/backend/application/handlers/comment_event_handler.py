"""Application-layer handlers for comment domain events.

These functions are fire-and-forget: they delegate to the notification
infrastructure, catch all exceptions, and log errors without re-raising.
This keeps the HTTP request path unaffected by notification failures.
"""

import logging

from backend.domain.aggregates.comment import Comment
from backend.domain.events.comment_posted import CommentPostedEvent
from backend.domain.events.mention_event import MentionEvent
from backend.domain.events.reply_received import ReplyReceivedEvent
from backend.infrastructure.notification.comment_notification_handler import (
    CommentNotificationHandler,
)
from backend.infrastructure.persistence.user_notification_preferences_repository import (  # noqa: E501
    UserNotificationPreferencesRepository,
)

logger = logging.getLogger(__name__)


def notify_comment_posted(
    comment: Comment,
    post_author_id: int,
    sender_id: int,
    handler: CommentNotificationHandler,
    preferences_repo: UserNotificationPreferencesRepository | None = None,
) -> None:
    """Queue a notification when a new top-level comment is posted.

    No notification is queued when the commenter is the post author, as
    authors do not need to be notified of their own comments. When
    preferences_repo is provided, the post author's reply notification
    preference is checked before queuing.

    Args:
        comment: The persisted Comment aggregate that was just created.
        post_author_id: User ID of the post author who should be notified.
        sender_id: User ID of the commenter.
        handler: CommentNotificationHandler used to persist the record.
        preferences_repo: Optional repository for fetching notification
            preferences. When provided, skips queuing if the recipient
            has disabled reply notifications.
    """
    if sender_id == post_author_id:
        return

    if preferences_repo is not None:
        prefs = preferences_repo.get_preferences(post_author_id)
        if not prefs.should_notify_reply():
            return

    try:
        if comment.id is None:
            raise ValueError(
                "comment.id must be set before queuing a notification"
            )
        event = CommentPostedEvent(
            comment_id=comment.id,
            post_id=comment.post_id,
            sender_id=sender_id,
            recipient_id=post_author_id,
        )
        handler.queue_comment_posted(event)
    except Exception:
        logger.exception("Failed to queue comment_posted notification")


def notify_reply_received(
    comment: Comment,
    parent_author_id: int,
    sender_id: int,
    handler: CommentNotificationHandler,
    preferences_repo: UserNotificationPreferencesRepository | None = None,
) -> None:
    """Queue a notification when a reply is posted to an existing comment.

    No notification is queued when the replier is the parent comment author,
    as users do not need to be notified of their own replies. When
    preferences_repo is provided, the parent author's reply notification
    preference is checked before queuing.

    Args:
        comment: The persisted reply Comment aggregate that was just created.
        parent_author_id: User ID of the parent comment author to notify.
        sender_id: User ID of the replier.
        handler: CommentNotificationHandler used to persist the record.
        preferences_repo: Optional repository for fetching notification
            preferences. When provided, skips queuing if the recipient
            has disabled reply notifications.
    """
    if sender_id == parent_author_id:
        return

    if preferences_repo is not None:
        prefs = preferences_repo.get_preferences(parent_author_id)
        if not prefs.should_notify_reply():
            return

    try:
        if comment.id is None:
            raise ValueError(
                "comment.id must be set before queuing a notification"
            )
        event = ReplyReceivedEvent(
            comment_id=comment.id,
            post_id=comment.post_id,
            sender_id=sender_id,
            recipient_id=parent_author_id,
        )
        handler.queue_reply_received(event)
    except Exception:
        logger.exception("Failed to queue reply_received notification")


def notify_mention(
    comment: Comment,
    sender_id: int,
    recipient_id: int,
    handler: CommentNotificationHandler,
    preferences_repo: UserNotificationPreferencesRepository | None = None,
) -> None:
    """Queue a notification when a user is @mentioned in a comment.

    No notification is queued when the sender and recipient are the same
    user (self-mention). When preferences_repo is provided, the recipient's
    mention notification preference is checked before queuing.

    Args:
        comment: The persisted Comment aggregate containing the mention.
        sender_id: User ID of the comment author who wrote the mention.
        recipient_id: User ID of the mentioned user to notify.
        handler: CommentNotificationHandler used to persist the record.
        preferences_repo: Optional repository for fetching notification
            preferences. When provided, skips queuing if the recipient
            has disabled mention notifications.
    """
    if sender_id == recipient_id:
        return

    if preferences_repo is not None:
        prefs = preferences_repo.get_preferences(recipient_id)
        if not prefs.should_notify_mention():
            return

    try:
        if comment.id is None:
            raise ValueError(
                "comment.id must be set before queuing a notification"
            )
        event = MentionEvent(
            comment_id=comment.id,
            post_id=comment.post_id,
            sender_id=sender_id,
            recipient_id=recipient_id,
        )
        handler.queue_mention(event)
    except Exception:
        logger.exception("Failed to queue mention notification")
