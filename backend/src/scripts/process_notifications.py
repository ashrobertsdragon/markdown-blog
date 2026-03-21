"""Background job: process notification queue via Resend.

Cron entry point for sending queued email notifications.
Exit codes: 0=success, 1=error
Usage: uv run scripts/process_notifications.py
       [--batch-limit N] [--max-queue-retries N] [--timeout N]
"""

import argparse
import fcntl
import logging
import os
import signal
import sys
from collections.abc import Callable
from typing import IO, NoReturn

from backend.application.commands.handlers import (
    process_notifications_handler,
)
from backend.application.commands.process_notifications_command import (
    ProcessNotificationsCommand,
)
from backend.config import ResendSettings
from backend.infrastructure.email.email_sender import EmailSender
from backend.infrastructure.email.resend_email_service import ResendEmailService
from backend.infrastructure.persistence.comment_repository import (
    CommentRepository,
)
from backend.infrastructure.persistence.notification_repository import (
    NotificationRepository,
)
from backend.infrastructure.persistence.post_repository import PostRepository
from backend.infrastructure.persistence.user_repository import UserRepository

logger = logging.getLogger(__name__)

_LOCK_FILE = "/tmp/process_notifications.lock"
_MAX_BATCH_LIMIT = 1000
_MAX_QUEUE_RETRIES = 10
_MAX_TIMEOUT_SECS = 300
_DEFAULT_TIMEOUT_SECS = 55


def setup_logging() -> None:
    """Configure logging for script execution."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )


def _bounded_int(lo: int, hi: int) -> Callable[[str], int]:
    """Return an argparse type function that validates an integer range."""

    def _validate(value: str) -> int:
        n = int(value)
        if not lo <= n <= hi:
            raise argparse.ArgumentTypeError(
                f"must be between {lo} and {hi}, got {n}"
            )
        return n

    return _validate


def parse_arguments(
    args: list[str] | None = None,
) -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Process queued email notifications via Resend"
    )
    parser.add_argument(
        "--batch-limit",
        type=_bounded_int(1, _MAX_BATCH_LIMIT),
        default=100,
        help=(
            "Maximum notifications to process per run"
            f" (1–{_MAX_BATCH_LIMIT}, default: 100)"
        ),
    )
    parser.add_argument(
        "--max-queue-retries",
        dest="max_retries",
        type=_bounded_int(0, _MAX_QUEUE_RETRIES),
        default=3,
        help=(
            "Maximum queue-level requeue attempts before marking"
            f" a notification permanently failed"
            f" (0–{_MAX_QUEUE_RETRIES}, default: 3)"
        ),
    )
    parser.add_argument(
        "--timeout",
        type=_bounded_int(1, _MAX_TIMEOUT_SECS),
        default=_DEFAULT_TIMEOUT_SECS,
        help=(
            "Wall-clock time limit in seconds before aborting"
            f" (1–{_MAX_TIMEOUT_SECS}, default: {_DEFAULT_TIMEOUT_SECS})"
        ),
    )
    return parser.parse_args(args)


def _acquire_lock() -> IO[str]:
    """Acquire an exclusive file lock to prevent concurrent cron runs.

    Raises:
        RuntimeError: If another instance is already running.
    """
    lock_file = open(_LOCK_FILE, "w")
    try:
        fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        lock_file.close()
        raise RuntimeError(
            "Another process_notifications instance is already running"
        )
    return lock_file


def _handle_timeout(signum: int, frame: object) -> NoReturn:
    """Handle SIGALRM by logging and exiting with error."""
    logger.error("Notification processor exceeded wall-clock limit — aborting")
    sys.exit(1)


def _get_dependencies() -> tuple[
    NotificationRepository,
    PostRepository,
    UserRepository,
    CommentRepository,
    EmailSender,
]:
    """Instantiate and return all required dependencies."""
    settings = ResendSettings()
    service = ResendEmailService(
        api_key=settings.RESEND_API_KEY,
        domain=settings.RESEND_DOMAIN,
        timeout=settings.RESEND_REQUEST_TIMEOUT,
        max_retries=settings.RESEND_MAX_RETRIES,
    )
    return (
        NotificationRepository(),
        PostRepository(),
        UserRepository(),
        CommentRepository(),
        EmailSender(service=service),
    )


def main() -> NoReturn:
    """Main entry point for notification processor script."""
    setup_logging()
    args = parse_arguments()

    try:
        lock_file = _acquire_lock()
    except RuntimeError as e:
        logger.error("Cannot acquire process lock: %s", e)
        sys.exit(1)

    with lock_file:
        signal.signal(signal.SIGALRM, _handle_timeout)
        signal.alarm(args.timeout)

        logger.info(
            "Starting notification processor"
            " (pid=%d, batch_limit=%d, max_retries=%d, timeout=%ds)",
            os.getpid(),
            args.batch_limit,
            args.max_retries,
            args.timeout,
        )

        try:
            (
                notification_repo,
                post_repo,
                user_repo,
                comment_repo,
                email_sender,
            ) = _get_dependencies()
        except Exception:
            logger.error(
                "Initialization failed —"
                " check environment variables and database connectivity"
            )
            sys.exit(1)

        site_base_url = os.environ.get("SITE_BASE_URL", "")

        try:
            command = ProcessNotificationsCommand(
                batch_limit=args.batch_limit,
                max_retries=args.max_retries,
                site_base_url=site_base_url,
            )

            summary = (
                process_notifications_handler.handle_process_notifications(
                    command=command,
                    notification_repo=notification_repo,
                    email_sender=email_sender,
                    post_repo=post_repo,
                    comment_repo=comment_repo,
                    user_repo=user_repo,
                )
            )

            signal.alarm(0)
            logger.info(
                "Notification processor completed:"
                " sent=%d, failed=%d, total=%d",
                summary.get("sent", 0),
                summary.get("failed", 0),
                summary.get("total", 0),
            )
            sys.exit(0)

        except Exception:
            logger.exception("Notification processor failed")
            sys.exit(1)


if __name__ == "__main__":
    main()
