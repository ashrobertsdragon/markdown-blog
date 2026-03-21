"""Health check script for notification queue.

Exits 0 if all metrics are within configured thresholds, 1 if any alert
condition is detected or an error occurs during initialisation.

Usage: uv run scripts/check_notification_health.py
       [--failure-threshold N] [--stuck-threshold-hours N]
"""

import argparse
import logging
import sys
from collections.abc import Callable

from backend.infrastructure.monitoring.notification_metrics import (
    NotificationMetrics,
)
from backend.infrastructure.persistence.notification_repository import (
    NotificationRepository,
)

logger = logging.getLogger(__name__)

_MIN_FAILURE_THRESHOLD = 0
_MAX_FAILURE_THRESHOLD = 100
_MIN_STUCK_HOURS = 1


def setup_logging() -> None:
    """Configure logging so output is captured correctly by cron.

    Cron-executed scripts have no TTY; basicConfig directs output to stderr,
    which cPanel cron captures in mail or log files. Format includes timestamp
    and level so operators can correlate alerts with cron schedules.
    """
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )


def _bounded_int(lo: int, hi: int) -> Callable[[str], int]:
    """Return an argparse type function enforcing an inclusive integer range.

    Args:
        lo: Inclusive lower bound.
        hi: Inclusive upper bound.

    Returns:
        Callable that converts a string to int and raises ArgumentTypeError
        if the value falls outside [lo, hi].
    """

    def _validate(value: str) -> int:
        try:
            n = int(value)
        except ValueError:
            raise argparse.ArgumentTypeError(
                f"expected an integer, got {value!r}"
            )
        if not lo <= n <= hi:
            raise argparse.ArgumentTypeError(
                f"must be between {lo} and {hi}, got {n}"
            )
        return n

    return _validate


def parse_arguments(
    args: list[str] | None = None,
) -> argparse.Namespace:
    """Parse and validate command-line arguments.

    Args:
        args: Argument list to parse. Defaults to sys.argv[1:] when None.

    Returns:
        Namespace with failure_threshold and stuck_threshold_hours attributes.
    """
    parser = argparse.ArgumentParser(
        description="Check notification queue health and emit alerts"
    )
    parser.add_argument(
        "--failure-threshold",
        type=_bounded_int(_MIN_FAILURE_THRESHOLD, _MAX_FAILURE_THRESHOLD),
        default=10,
        help=(
            "Failure rate percentage above which an alert is triggered"
            f" ({_MIN_FAILURE_THRESHOLD}–{_MAX_FAILURE_THRESHOLD},"
            " default: 10)"
        ),
    )
    parser.add_argument(
        "--stuck-threshold-hours",
        type=_bounded_int(_MIN_STUCK_HOURS, 24 * 7),
        default=1,
        help=(
            "Age in hours beyond which a PENDING notification is stuck"
            f" (>={_MIN_STUCK_HOURS}, default: 1)"
        ),
    )
    return parser.parse_args(args)


def main() -> None:
    """Run health check and exit with an appropriate status code.

    Exit codes:
        0 — all metrics within thresholds (healthy)
        1 — at least one alert condition detected, or initialisation failed
    """
    setup_logging()
    args = parse_arguments()

    try:
        repository = NotificationRepository()
        metrics = NotificationMetrics(repository)
    except Exception as exc:
        logger.error(
            "Initialisation failed (%s) — check environment variables"
            " and database connectivity",
            type(exc).__name__,
        )
        sys.exit(1)

    summary = metrics.get_health_summary(stuck_hours=args.stuck_threshold_hours)

    logger.info(
        "Health summary: sent=%d, failed=%d, pending=%d,"
        " failure_rate=%.1f%%, stuck=%d, timestamp=%s",
        summary["sent"],
        summary["failed"],
        summary["pending"],
        summary["failure_rate"],
        summary["stuck_count"],
        summary["timestamp"],
    )

    alert_triggered = False

    if summary["failure_rate"] > args.failure_threshold:
        logger.warning(
            "ALERT: failure rate %.1f%% exceeds threshold %d%%",
            summary["failure_rate"],
            args.failure_threshold,
        )
        alert_triggered = True

    if summary["stuck_count"] > 0:
        logger.warning(
            "ALERT: %d notification(s) stuck for > %d hour(s)",
            summary["stuck_count"],
            args.stuck_threshold_hours,
        )
        alert_triggered = True

    if alert_triggered:
        logger.info("Status: ALERT")
        sys.exit(1)

    logger.info("Status: HEALTHY")
    sys.exit(0)


if __name__ == "__main__":
    main()
