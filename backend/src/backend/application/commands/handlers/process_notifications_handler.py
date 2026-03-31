"""Handler for ProcessNotificationsCommand.

This module implements the handler function that fetches pending notifications
and delivers them via email, applying exponential backoff retry logic.
"""

import logging
from datetime import UTC, datetime, timedelta

from backend.application.commands.process_notifications_command import (
    ProcessNotificationsCommand,
)
from backend.domain.value_objects.unsubscribe_token import UnsubscribeToken
from backend.infrastructure.email.email_sender import EmailSender
from backend.infrastructure.persistence.comment_repository import (
    CommentRepository,
)
from backend.infrastructure.persistence.notification_repository import (
    NotificationRepository,
)
from backend.infrastructure.persistence.post_repository import PostRepository
from backend.infrastructure.persistence.user_repository import UserRepository

logger = logging.getLogger(__name__)

_RETRY_DELAYS_MINUTES = [1, 5, 15]


def _truncate(text: str, max_len: int = 200) -> str:
    """Return text truncated to max_len characters with ellipsis if needed.

    Args:
        text: The source string.
        max_len: Maximum character length before truncation.

    Returns:
        Original text when within max_len, or text[:max_len] + '...'
    """
    if len(text) > max_len:
        return text[:max_len] + "..."
    return text


def _build_unsubscribe_url(recipient_id: int, recipient_email: str) -> str:
    """Build an unsubscribe URL carrying an HMAC token for the recipient.

    Returns an empty string if SECRET_KEY is not configured rather than
    emitting an unauthenticated URL that could be exploited to unsubscribe
    any user by guessing their integer ID.

    Args:
        recipient_id: Primary key of the recipient User.
        recipient_email: Email address of the recipient.

    Returns:
        URL string of the form /unsubscribe?token={token_value}, or
        empty string when SECRET_KEY is absent.
    """
    try:
        token = UnsubscribeToken.generate(recipient_id, recipient_email)
        return f"/unsubscribe?user_id={recipient_id}&token={token.value}"
    except (KeyError, ValueError):
        logger.warning(
            "SECRET_KEY not configured; omitting unsubscribe URL for user %d",
            recipient_id,
        )
        return ""


def _build_variables(
    event_type: str,
    sender_name: str,
    post_title: str,
    comment_text: str,
    post_url: str,
    unsubscribe_url: str,
) -> dict[str, str]:
    """Build the template variable dict for the given event type.

    Args:
        event_type: Domain event discriminator string.
        sender_name: Display name or email of the notification sender.
        post_title: Title of the related post.
        comment_text: Body text of the triggering comment.
        post_url: Absolute URL to the post page.
        unsubscribe_url: Personalised unsubscribe link for the recipient.

    Returns:
        Dictionary of template variable names to string values.
    """
    excerpt = _truncate(comment_text)

    match event_type:
        case "mention":
            return {
                "MENTION_AUTHOR": sender_name,
                "POST_TITLE": post_title,
                "MENTION_CONTEXT": excerpt,
                "POST_URL": post_url,
                "UNSUBSCRIBE_URL": unsubscribe_url,
            }
        case "comment_posted":
            return {
                "REPLY_AUTHOR": sender_name,
                "POST_TITLE": post_title,
                "ORIGINAL_COMMENT": excerpt,
                "REPLY_EXCERPT": "",
                "POST_URL": post_url,
                "UNSUBSCRIBE_URL": unsubscribe_url,
            }
        case _:
            return {
                "REPLY_AUTHOR": sender_name,
                "POST_TITLE": post_title,
                "ORIGINAL_COMMENT": "",
                "REPLY_EXCERPT": excerpt,
                "POST_URL": post_url,
                "UNSUBSCRIBE_URL": unsubscribe_url,
            }


def _retry_delay(attempt_count: int) -> timedelta:
    """Return the backoff delay for the given attempt count.

    Args:
        attempt_count: Number of delivery attempts already made.

    Returns:
        timedelta for the next retry window.

    Note:
        At the default max_retries=3, only the first two entries (1 min, 5 min)
        are reachable. The 15-minute entry applies when max_retries exceeds 3.
    """
    index = min(attempt_count, len(_RETRY_DELAYS_MINUTES) - 1)
    return timedelta(minutes=_RETRY_DELAYS_MINUTES[index])


def handle_process_notifications(
    command: ProcessNotificationsCommand,
    notification_repo: NotificationRepository,
    email_sender: EmailSender,
    post_repo: PostRepository,
    comment_repo: CommentRepository,
    user_repo: UserRepository,
) -> dict[str, int]:
    """Handle ProcessNotificationsCommand to deliver pending notifications.

    Fetches up to command.batch_limit pending notifications and attempts
    email delivery for each. On success records the Resend email ID. On
    failure schedules a retry with exponential backoff or marks the
    notification permanently failed when max_retries is exhausted.

    Exceptions raised during processing of individual notifications are
    caught and logged; processing continues for remaining notifications.

    Args:
        command: ProcessNotificationsCommand with batch_limit and max_retries.
        notification_repo: NotificationRepository for fetching and updating
            notification records.
        email_sender: EmailSender for delivering emails via Resend.
        post_repo: Repository providing find_by_id for Post lookup.
        comment_repo: Repository providing find_by_id for Comment lookup.
        user_repo: Repository providing find_by_id for User lookup.

    Returns:
        Summary dict with keys 'sent', 'failed', and 'total'.
    """
    notifications = notification_repo.get_pending(command.batch_limit)
    logger.info("Fetched %d pending notifications", len(notifications))
    sent = 0
    failed = 0

    for notification in notifications:
        try:
            if notification.id is None:
                logger.warning("Skipping notification with no id")
                failed += 1
                continue

            recipient = user_repo.find_by_id(notification.recipient_id)
            sender = user_repo.find_by_id(notification.sender_id)
            post = post_repo.find_by_id(notification.post_id)
            comment = comment_repo.find_by_id(notification.comment_id)

            if (
                recipient is None
                or sender is None
                or post is None
                or comment is None
            ):
                logger.warning(
                    "Skipping notification %d: missing context (recipient=%s, "
                    "sender=%s, post=%s, comment=%s)",
                    notification.id,
                    recipient is None,
                    sender is None,
                    post is None,
                    comment is None,
                )
                notification.mark_failed(
                    "Missing context: referenced entity not found"
                )
                notification_repo.save(notification)
                failed += 1
                continue

            recipient_email = recipient.email
            sender_name = getattr(sender, "name", None) or "A blog user"
            post_title = post.title
            comment_text = str(getattr(comment, "text", "")) or ""
            post_url = f"{command.site_base_url}/posts/{notification.post_id}"
            unsubscribe_url = _build_unsubscribe_url(
                notification.recipient_id, recipient_email
            )

            variables = _build_variables(
                event_type=str(notification.event_type),
                sender_name=sender_name,
                post_title=post_title,
                comment_text=comment_text,
                post_url=post_url,
                unsubscribe_url=unsubscribe_url,
            )

            email_id = email_sender.send(
                recipient_email,
                notification.event_type,
                variables,
            )

            if isinstance(email_id, str):
                notification.mark_sent(email_id)
                notification_repo.save(notification)
                sent += 1
            else:
                notification.increment_attempt()
                new_count = notification.attempt_count
                if new_count >= command.max_retries:
                    notification.mark_failed("Max retries exceeded")
                    notification_repo.save(notification)
                else:
                    next_retry_at = datetime.now(UTC) + _retry_delay(
                        new_count - 1
                    )
                    notification_repo.save(notification)
                    notification_repo.mark_for_retry(
                        notification.id, next_retry_at
                    )
                failed += 1

        except Exception:
            logger.exception(
                "Unhandled error processing notification %s",
                getattr(notification, "id", None),
            )
            failed += 1

    return {"sent": sent, "failed": failed, "total": sent + failed}
