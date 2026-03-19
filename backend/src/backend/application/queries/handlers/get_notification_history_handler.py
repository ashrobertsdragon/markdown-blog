"""Handler for GetNotificationHistoryQuery.

This module implements the handler function that retrieves and enriches
a paginated notification history for a user.
"""

import logging

from backend.application.queries.get_notification_history_query import (
    GetNotificationHistoryQuery,
    GetNotificationHistoryResponse,
    NotificationHistoryItem,
)
from backend.domain.aggregates.notification import Notification
from backend.infrastructure.persistence.notification_repository import (
    NotificationRepository,
)
from backend.infrastructure.persistence.post_repository import PostRepository
from backend.infrastructure.persistence.user_repository import UserRepository

logger = logging.getLogger(__name__)


def handle_get_notification_history(
    query: GetNotificationHistoryQuery,
    notification_repo: NotificationRepository,
    post_repo: PostRepository,
    user_repo: UserRepository,
) -> GetNotificationHistoryResponse:
    """Handle GetNotificationHistoryQuery to list notifications for a user.

    Uses limit+1 to determine whether more items follow the current page
    without a separate count query.

    Args:
        query: GetNotificationHistoryQuery carrying user_id, skip, and limit.
        notification_repo: Repository providing get_history for fetching
            notification records.
        post_repo: Repository providing find_by_id for Post title lookup.
        user_repo: Repository providing find_by_id for recipient info lookup.

    Returns:
        GetNotificationHistoryResponse with items and has_more.
    """
    logger.debug(
        "Fetching notification history for user %d (skip=%d, limit=%d)",
        query.user_id,
        query.skip,
        query.limit,
    )

    raw = notification_repo.list_for_user(
        query.user_id, skip=query.skip, limit=query.limit + 1
    )

    has_more = len(raw) > query.limit
    notifications = raw[: query.limit]

    items = [_to_history_item(n, post_repo, user_repo) for n in notifications]

    return GetNotificationHistoryResponse(items=items, has_more=has_more)


def _to_history_item(
    notification: Notification,
    post_repo: PostRepository,
    user_repo: UserRepository,
) -> NotificationHistoryItem:
    """Convert a Notification aggregate to a NotificationHistoryItem DTO.

    Args:
        notification: Notification aggregate to convert.
        post_repo: Repository for Post lookup by id.
        user_repo: Repository for User lookup by id.

    Returns:
        NotificationHistoryItem populated with enriched data.
    """
    post = post_repo.get_by_id(notification.post_id)
    post_title = post.title if post else ""

    recipient = user_repo.get_by_id(notification.recipient_id)
    recipient_email = recipient.email if recipient else ""

    created_at_str = notification.created_at.isoformat()
    sent_at_str = (
        notification.sent_at.isoformat() if notification.sent_at else None
    )

    if notification.id is None:
        raise ValueError("Persisted notification missing id")

    return NotificationHistoryItem(
        id=notification.id,
        recipient_email=recipient_email,
        event_type=str(notification.event_type),
        post_title=post_title,
        status=str(notification.status),
        created_at=created_at_str,
        sent_at=sent_at_str,
        error_message=notification.error_message,
        resend_email_id=None,
    )
