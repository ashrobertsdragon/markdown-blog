"""Notification queue health metrics calculation.

Provides aggregate metrics over the notification queue to support
operational monitoring, alerting, and health check scripts. Deliberately
placed in infrastructure so cron scripts can import it without pulling in
the full application layer; all business-rule thresholds live in the caller.
"""

from datetime import UTC, datetime, timedelta
from typing import TypedDict

from backend.domain.aggregates.notification import Notification
from backend.infrastructure.persistence.notification_repository import (
    NotificationRepository,
)


class HealthSummary(TypedDict):
    """Typed structure for notification queue health snapshot."""

    sent: int
    failed: int
    pending: int
    failure_rate: float
    stuck_count: int
    timestamp: str


class NotificationMetrics:
    """Calculate health metrics for the notification queue.

    Queries the repository for counts and pending notifications to derive
    failure rates and detect stalled deliveries that warrant operator
    intervention.
    """

    def __init__(self, repository: NotificationRepository) -> None:
        """Bind metrics calculations to a notification repository.

        Args:
            repository: Source of notification counts and pending records.
        """
        self.repository = repository

    def calculate_totals(self) -> dict[str, int]:
        """Return per-status notification counts from the repository.

        Returns:
            Dict with keys 'sent', 'failed', and 'pending', each mapped
            to the integer count of notifications in that state.
        """
        return {
            "sent": self.repository.count_sent(),
            "failed": self.repository.count_failed(),
            "pending": self.repository.count_pending(),
        }

    def calculate_failure_rate(self) -> float:
        """Return the failure rate as a percentage over terminal notifications.

        Failure rate is defined as failed / (sent + failed) * 100. Pending
        notifications are excluded from the denominator because they have
        not yet reached a terminal state. Returns 0.0 when no terminal
        notifications exist to avoid division by zero.

        Returns:
            Float in the range [0.0, 100.0].
        """
        sent = self.repository.count_sent()
        failed = self.repository.count_failed()
        terminal = sent + failed
        if terminal == 0:
            return 0.0
        return (failed / terminal) * 100

    def detect_stuck_notifications(self, hours: int = 1) -> list[Notification]:
        """Return pending notifications that have exceeded the age threshold.

        A notification is considered stuck when it remains in PENDING status
        for longer than the threshold, suggesting the processor is not
        consuming it (e.g. misconfiguration, worker failure).

        Args:
            hours: Age threshold in hours. Notifications older than this are
                   considered stuck. Must be >= 1. Defaults to 1.

        Returns:
            List of Notification domain objects whose created_at precedes
            the cutoff, preserving repository order.
        """
        cutoff = datetime.now(UTC) - timedelta(hours=hours)
        pending = self.repository.get_pending()
        return [n for n in pending if n.created_at < cutoff]

    def get_health_summary(self, stuck_hours: int = 1) -> HealthSummary:
        """Return a complete snapshot of notification queue health.

        Fetches totals once and derives failure rate inline to avoid redundant
        database round-trips. Combines totals, failure rate, stuck count, and
        a UTC timestamp into a single dict suitable for logging or structured
        alert output.

        Args:
            stuck_hours: Age threshold in hours for stuck-notification
                detection. Forwarded to detect_stuck_notifications so callers
                can use operator-configured values instead of the default.

        Returns:
            Dict with keys: 'sent', 'failed', 'pending', 'failure_rate',
            'stuck_count', 'timestamp' (ISO 8601 string).
        """
        sent = self.repository.count_sent()
        failed = self.repository.count_failed()
        pending = self.repository.count_pending()
        terminal = sent + failed
        failure_rate = (failed / terminal * 100) if terminal else 0.0
        stuck = self.detect_stuck_notifications(hours=stuck_hours)
        return HealthSummary(
            sent=sent,
            failed=failed,
            pending=pending,
            failure_rate=failure_rate,
            stuck_count=len(stuck),
            timestamp=datetime.now(UTC).isoformat(),
        )
