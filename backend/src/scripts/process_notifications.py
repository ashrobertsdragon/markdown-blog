"""Background job: process notification queue via Resend.

Cron entry point for sending queued email notifications.
Exit codes: 0=success, 1=error
Usage: uv run scripts/process_notifications.py
       [--batch-limit N] [--max-retries N]
"""

import argparse
import logging
import sys
from typing import NoReturn

from backend.application.commands.handlers import (
    process_notifications_handler,
)
from backend.application.commands.process_notifications_command import (
    ProcessNotificationsCommand,
)
from backend.config import ResendSettings
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


def setup_logging() -> None:
    """Configure logging for script execution."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )


def parse_arguments(
    args: list[str] | None = None,
) -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Process queued email notifications via Resend"
    )
    parser.add_argument(
        "--batch-limit",
        type=int,
        default=100,
        help="Maximum notifications to process per run (default: 100)",
    )
    parser.add_argument(
        "--max-retries",
        type=int,
        default=3,
        help="Maximum delivery attempts per notification (default: 3)",
    )
    return parser.parse_args(args)


def _get_dependencies() -> tuple[
    NotificationRepository,
    PostRepository,
    UserRepository,
    CommentRepository,
    EmailSender,
]:
    """Instantiate and return all required dependencies."""
    settings = ResendSettings()
    return (
        NotificationRepository(),
        PostRepository(),
        UserRepository(),
        CommentRepository(),
        EmailSender(
            api_key=settings.RESEND_API_KEY,
            domain=settings.RESEND_DOMAIN,
            timeout=settings.RESEND_REQUEST_TIMEOUT,
            max_retries=settings.RESEND_MAX_RETRIES,
        ),
    )


def main() -> NoReturn:
    """Main entry point for notification processor script."""
    setup_logging()
    args = parse_arguments()

    try:
        logger.info(
            "Starting notification processor (batch_limit=%d, max_retries=%d)",
            args.batch_limit,
            args.max_retries,
        )

        notification_repo, post_repo, user_repo, comment_repo, email_sender = (
            _get_dependencies()
        )

        command = ProcessNotificationsCommand(
            batch_limit=args.batch_limit,
            max_retries=args.max_retries,
        )

        summary = process_notifications_handler.handle_process_notifications(
            command=command,
            notification_repo=notification_repo,
            email_sender=email_sender,
            post_repo=post_repo,
            comment_repo=comment_repo,
            user_repo=user_repo,
        )

        logger.info(
            "Notification processor completed: sent=%d, failed=%d, total=%d",
            summary["sent"],
            summary["failed"],
            summary["total"],
        )
        sys.exit(0)

    except Exception:
        logger.exception("Notification processor failed")
        sys.exit(1)


if __name__ == "__main__":
    main()
