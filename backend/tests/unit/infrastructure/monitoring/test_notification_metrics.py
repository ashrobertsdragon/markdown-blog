"""Unit tests for NotificationMetrics class.

Tests cover metrics calculation, stuck notification detection, and
health summary construction. All tests use mock repositories to remain
isolated from the database layer.
"""

from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock

import pytest
from backend.infrastructure.monitoring.notification_metrics import (
    NotificationMetrics,
)


def _make_repo(
    *,
    sent: int = 0,
    failed: int = 0,
    pending: int = 0,
    pending_notifications: list | None = None,
) -> MagicMock:
    """Build a mock NotificationRepository with configurable counts."""
    repo = MagicMock()
    repo.count_sent.return_value = sent
    repo.count_failed.return_value = failed
    repo.count_pending.return_value = pending
    repo.get_pending.return_value = pending_notifications or []
    return repo


def _make_notification(created_at: datetime) -> MagicMock:
    """Build a mock Notification with the given created_at timestamp."""
    notification = MagicMock()
    notification.created_at = created_at
    return notification


class TestNotificationMetricsBasics:
    """NotificationMetrics initialises and exposes repository."""

    def test_init_accepts_notification_repository(self) -> None:
        """NotificationMetrics accepts a repository on construction."""
        repo = _make_repo()
        metrics = NotificationMetrics(repo)
        assert metrics is not None

    def test_init_stores_repository(self) -> None:
        """Repository is stored and accessible for calculations."""
        repo = _make_repo()
        metrics = NotificationMetrics(repo)
        assert metrics.repository is repo

    def test_calculate_totals_returns_dict(self) -> None:
        """calculate_totals returns a dictionary."""
        metrics = NotificationMetrics(_make_repo(sent=1, failed=2, pending=3))
        result = metrics.calculate_totals()
        assert isinstance(result, dict)

    def test_calculate_totals_returns_sent_count(self) -> None:
        """calculate_totals includes sent count from repository."""
        metrics = NotificationMetrics(_make_repo(sent=5))
        result = metrics.calculate_totals()
        assert result["sent"] == 5

    def test_calculate_totals_returns_pending_count(self) -> None:
        """calculate_totals includes pending count from repository."""
        metrics = NotificationMetrics(_make_repo(pending=3))
        result = metrics.calculate_totals()
        assert result["pending"] == 3

    def test_calculate_totals_returns_failed_count(self) -> None:
        """calculate_totals includes failed count from repository."""
        metrics = NotificationMetrics(_make_repo(failed=7))
        result = metrics.calculate_totals()
        assert result["failed"] == 7


class TestFailureRateCalculation:
    """Failure rate is calculated correctly across all boundary conditions."""

    def test_failure_rate_is_zero_when_no_notifications(self) -> None:
        """Failure rate is 0.0 when no sent or failed notifications exist."""
        metrics = NotificationMetrics(_make_repo(sent=0, failed=0))
        assert metrics.calculate_failure_rate() == 0.0

    def test_failure_rate_is_zero_when_all_sent(self) -> None:
        """Failure rate is 0.0 when all notifications were delivered."""
        metrics = NotificationMetrics(_make_repo(sent=10, failed=0))
        assert metrics.calculate_failure_rate() == 0.0

    def test_failure_rate_calculation(self) -> None:
        """Failure rate equals failed / (sent + failed) * 100."""
        metrics = NotificationMetrics(_make_repo(sent=9, failed=1))
        assert metrics.calculate_failure_rate() == pytest.approx(10.0)

    def test_failure_rate_is_100_when_all_failed(self) -> None:
        """Failure rate is 100.0 when every notification failed."""
        metrics = NotificationMetrics(_make_repo(sent=0, failed=5))
        assert metrics.calculate_failure_rate() == 100.0

    @pytest.mark.parametrize(
        ("sent", "failed", "expected_rate"),
        [
            (90, 10, 10.0),
            (50, 50, 50.0),
            (1, 99, 99.0),
            (99, 1, pytest.approx(1.0, abs=0.01)),
            (3, 1, 25.0),
        ],
    )
    def test_failure_rate_parametrized(
        self, sent: int, failed: int, expected_rate: float
    ) -> None:
        """Failure rate is correct for a range of sent/failed combinations."""
        metrics = NotificationMetrics(_make_repo(sent=sent, failed=failed))
        assert metrics.calculate_failure_rate() == expected_rate

    def test_failure_rate_excludes_pending_from_denominator(self) -> None:
        """Pending notifications are not included in the failure rate."""
        metrics = NotificationMetrics(_make_repo(sent=8, failed=2, pending=100))
        assert metrics.calculate_failure_rate() == pytest.approx(20.0)


class TestStuckNotificationDetection:
    """Stuck notifications are identified by age and status."""

    def test_empty_list_when_no_pending(self) -> None:
        """detect_stuck_notifications returns empty list when no pending."""
        metrics = NotificationMetrics(_make_repo(pending_notifications=[]))
        assert metrics.detect_stuck_notifications() == []

    def test_excludes_recently_created_notifications(self) -> None:
        """Notifications created within the threshold are not stuck."""
        recent = _make_notification(
            created_at=datetime.now(UTC) - timedelta(minutes=30)
        )
        metrics = NotificationMetrics(
            _make_repo(pending_notifications=[recent])
        )
        result = metrics.detect_stuck_notifications(hours=1)
        assert len(result) == 0

    def test_includes_old_pending_notifications(self) -> None:
        """Notifications older than the threshold are stuck."""
        old = _make_notification(
            created_at=datetime.now(UTC) - timedelta(hours=2)
        )
        metrics = NotificationMetrics(_make_repo(pending_notifications=[old]))
        result = metrics.detect_stuck_notifications(hours=1)
        assert len(result) == 1
        assert result[0] is old

    def test_filters_by_created_at_threshold(self) -> None:
        """Only notifications created before the cutoff are returned."""
        old = _make_notification(
            created_at=datetime.now(UTC) - timedelta(hours=3)
        )
        recent = _make_notification(
            created_at=datetime.now(UTC) - timedelta(minutes=10)
        )
        metrics = NotificationMetrics(
            _make_repo(pending_notifications=[old, recent])
        )
        result = metrics.detect_stuck_notifications(hours=1)
        assert len(result) == 1
        assert result[0] is old

    def test_default_threshold_is_one_hour(self) -> None:
        """Default stuck threshold is 1 hour when not specified."""
        stuck = _make_notification(
            created_at=datetime.now(UTC) - timedelta(minutes=61)
        )
        not_stuck = _make_notification(
            created_at=datetime.now(UTC) - timedelta(minutes=59)
        )
        metrics = NotificationMetrics(
            _make_repo(pending_notifications=[stuck, not_stuck])
        )
        result = metrics.detect_stuck_notifications()
        assert len(result) == 1
        assert result[0] is stuck

    def test_custom_threshold_in_hours(self) -> None:
        """Custom threshold correctly overrides the 1-hour default."""
        stuck = _make_notification(
            created_at=datetime.now(UTC) - timedelta(hours=3)
        )
        ok = _make_notification(
            created_at=datetime.now(UTC) - timedelta(hours=1)
        )
        metrics = NotificationMetrics(
            _make_repo(pending_notifications=[stuck, ok])
        )
        result = metrics.detect_stuck_notifications(hours=2)
        assert len(result) == 1
        assert result[0] is stuck

    def test_returns_all_stuck_when_multiple_old(self) -> None:
        """All notifications older than the threshold are returned."""
        old_1 = _make_notification(
            created_at=datetime.now(UTC) - timedelta(hours=5)
        )
        old_2 = _make_notification(
            created_at=datetime.now(UTC) - timedelta(hours=2)
        )
        metrics = NotificationMetrics(
            _make_repo(pending_notifications=[old_1, old_2])
        )
        result = metrics.detect_stuck_notifications(hours=1)
        assert len(result) == 2


class TestHealthSummary:
    """get_health_summary returns a complete, structured dict."""

    def test_health_summary_includes_totals(self) -> None:
        """Health summary contains sent, pending, and failed counts."""
        metrics = NotificationMetrics(_make_repo(sent=10, failed=1, pending=2))
        summary = metrics.get_health_summary()
        assert summary["sent"] == 10
        assert summary["failed"] == 1
        assert summary["pending"] == 2

    def test_health_summary_includes_failure_rate(self) -> None:
        """Health summary includes computed failure_rate field."""
        metrics = NotificationMetrics(_make_repo(sent=9, failed=1))
        summary = metrics.get_health_summary()
        assert "failure_rate" in summary
        assert summary["failure_rate"] == pytest.approx(10.0)

    def test_health_summary_includes_stuck_count(self) -> None:
        """Health summary includes count of stuck notifications."""
        old = _make_notification(
            created_at=datetime.now(UTC) - timedelta(hours=2)
        )
        metrics = NotificationMetrics(
            _make_repo(sent=5, pending=1, pending_notifications=[old])
        )
        summary = metrics.get_health_summary()
        assert "stuck_count" in summary
        assert summary["stuck_count"] == 1

    def test_health_summary_includes_timestamp(self) -> None:
        """Health summary includes an ISO 8601 timestamp."""
        metrics = NotificationMetrics(_make_repo())
        summary = metrics.get_health_summary()
        assert "timestamp" in summary
        datetime.fromisoformat(summary["timestamp"])

    def test_health_summary_structure_is_complete(self) -> None:
        """Health summary contains exactly the expected keys."""
        metrics = NotificationMetrics(_make_repo())
        summary = metrics.get_health_summary()
        expected_keys = {
            "sent",
            "failed",
            "pending",
            "failure_rate",
            "stuck_count",
            "timestamp",
        }
        assert set(summary.keys()) == expected_keys
