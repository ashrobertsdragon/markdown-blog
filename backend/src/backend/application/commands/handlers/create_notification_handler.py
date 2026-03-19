"""Handler for CreateNotificationCommand.

This module implements the handler function that creates and persists a
Notification aggregate after checking the recipient's notification preferences.
"""

import logging

from backend.application.commands.create_notification_command import (
    CreateNotificationCommand,
)
from backend.domain.aggregates.notification import EventType, Notification
from backend.infrastructure.persistence.notification_repository import (
    NotificationRepository,
)
from backend.infrastructure.persistence.user_notification_preferences_repository import (  # noqa: E501
    UserNotificationPreferencesRepository,
)

logger = logging.getLogger(__name__)


def handle_create_notification(
    command: CreateNotificationCommand,
    notification_repo: NotificationRepository,
    preferences_repo: UserNotificationPreferencesRepository,
) -> Notification | None:
    """Handle CreateNotificationCommand to persist a new notification.

    Checks the recipient's notification preferences before creating the
    record. Returns None without saving when the relevant preference is
    disabled.

    Args:
        command: CreateNotificationCommand carrying recipient_id, sender_id,
            event_type, post_id, and comment_id.
        notification_repo: NotificationRepository used to persist the record.
        preferences_repo: UserNotificationPreferencesRepository used to
            fetch recipient preferences.

    Returns:
        Persisted Notification aggregate, or None when the preference is
        disabled.
    """
    prefs = preferences_repo.get_preferences(command.recipient_id)

    match command.event_type:
        case "mention":
            if not prefs.should_notify_mention():
                logger.debug(
                    "Skipping mention notification for recipient %d"
                    " (preference disabled)",
                    command.recipient_id,
                )
                return None
        case "comment_posted":
            if not prefs.should_notify_reply():
                logger.debug(
                    "Skipping %s notification for recipient %d"
                    " (preference disabled)",
                    command.event_type,
                    command.recipient_id,
                )
                return None
        case "reply_received":
            if not prefs.should_notify_reply():
                logger.debug(
                    "Skipping %s notification for recipient %d"
                    " (preference disabled)",
                    command.event_type,
                    command.recipient_id,
                )
                return None
        case _:
            logger.warning(
                "Unknown event_type %s; skipping notification",
                command.event_type,
            )
            return None

    notification = Notification.create(
        recipient_id=command.recipient_id,
        sender_id=command.sender_id,
        event_type=EventType(command.event_type),
        post_id=command.post_id,
        comment_id=command.comment_id,
    )

    return notification_repo.save(notification)
