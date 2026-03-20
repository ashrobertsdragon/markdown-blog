"""Unit tests for check_notification_health background script.

Tests cover argument parsing, exit codes, alert logic, logging behaviour,
and dependency initialisation. All external dependencies are mocked so
no database or network access is required.
"""

import logging
from unittest.mock import MagicMock, patch

import pytest

SCRIPT_MODULE = "scripts.check_notification_health"
METRICS_PATH = f"{SCRIPT_MODULE}.NotificationMetrics"
NOTIFICATION_REPO_PATH = f"{SCRIPT_MODULE}.NotificationRepository"
ARGV_PATH = "sys.argv"
DEFAULT_ARGV = ["check_notification_health.py"]


def _make_metrics(
    *,
    sent: int = 10,
    failed: int = 0,
    pending: int = 0,
    failure_rate: float = 0.0,
    stuck_count: int = 0,
    timestamp: str = "2026-03-20T00:00:00+00:00",
) -> MagicMock:
    """Build a mock NotificationMetrics instance with a fixed health summary."""
    metrics = MagicMock()
    metrics.get_health_summary.return_value = {
        "sent": sent,
        "failed": failed,
        "pending": pending,
        "failure_rate": failure_rate,
        "stuck_count": stuck_count,
        "timestamp": timestamp,
    }
    return metrics


class TestArgumentParsing:
    """CLI flags are parsed and validated correctly."""

    def test_default_failure_threshold_is_10(self) -> None:
        """--failure-threshold defaults to 10."""
        from scripts.check_notification_health import parse_arguments

        args = parse_arguments([])
        assert args.failure_threshold == 10

    def test_default_stuck_threshold_hours_is_1(self) -> None:
        """--stuck-threshold-hours defaults to 1."""
        from scripts.check_notification_health import parse_arguments

        args = parse_arguments([])
        assert args.stuck_threshold_hours == 1

    def test_custom_failure_threshold(self) -> None:
        """--failure-threshold accepts a custom percentage value."""
        from scripts.check_notification_health import parse_arguments

        args = parse_arguments(["--failure-threshold", "25"])
        assert args.failure_threshold == 25

    def test_custom_stuck_threshold_hours(self) -> None:
        """--stuck-threshold-hours accepts a custom hour value."""
        from scripts.check_notification_health import parse_arguments

        args = parse_arguments(["--stuck-threshold-hours", "2"])
        assert args.stuck_threshold_hours == 2

    def test_both_flags_together(self) -> None:
        """Both flags can be supplied simultaneously."""
        from scripts.check_notification_health import parse_arguments

        args = parse_arguments(
            ["--failure-threshold", "15", "--stuck-threshold-hours", "3"]
        )
        assert args.failure_threshold == 15
        assert args.stuck_threshold_hours == 3

    def test_failure_threshold_below_zero_rejected(self) -> None:
        """--failure-threshold rejects values below 0."""
        from scripts.check_notification_health import parse_arguments

        with pytest.raises(SystemExit):
            parse_arguments(["--failure-threshold", "-1"])

    def test_failure_threshold_above_100_rejected(self) -> None:
        """--failure-threshold rejects values above 100."""
        from scripts.check_notification_health import parse_arguments

        with pytest.raises(SystemExit):
            parse_arguments(["--failure-threshold", "101"])


class TestHealthCheckExitCodes:
    """Script exits with appropriate codes for health and alert states."""

    def test_exits_zero_when_healthy(self) -> None:
        """Exit code 0 when failure rate and stuck count are within bounds."""
        from scripts.check_notification_health import main

        with (
            patch(ARGV_PATH, DEFAULT_ARGV),
            patch(NOTIFICATION_REPO_PATH),
            patch(METRICS_PATH, return_value=_make_metrics()),
        ):
            with pytest.raises(SystemExit) as exc_info:
                main()

        assert exc_info.value.code == 0

    def test_exits_one_when_failure_rate_exceeds_threshold(self) -> None:
        """Exit code 1 when failure rate exceeds --failure-threshold."""
        from scripts.check_notification_health import main

        with (
            patch(ARGV_PATH, DEFAULT_ARGV),
            patch(NOTIFICATION_REPO_PATH),
            patch(
                METRICS_PATH,
                return_value=_make_metrics(failure_rate=15.0),
            ),
        ):
            with pytest.raises(SystemExit) as exc_info:
                main()

        assert exc_info.value.code == 1

    def test_exits_one_when_stuck_notifications_detected(self) -> None:
        """Exit code 1 when stuck notifications exceed zero."""
        from scripts.check_notification_health import main

        with (
            patch(ARGV_PATH, DEFAULT_ARGV),
            patch(NOTIFICATION_REPO_PATH),
            patch(
                METRICS_PATH,
                return_value=_make_metrics(stuck_count=2),
            ),
        ):
            with pytest.raises(SystemExit) as exc_info:
                main()

        assert exc_info.value.code == 1

    def test_exits_one_when_both_alerts_triggered(self) -> None:
        """Exit code 1 when both failure rate and stuck count alert."""
        from scripts.check_notification_health import main

        with (
            patch(ARGV_PATH, DEFAULT_ARGV),
            patch(NOTIFICATION_REPO_PATH),
            patch(
                METRICS_PATH,
                return_value=_make_metrics(failure_rate=20.0, stuck_count=3),
            ),
        ):
            with pytest.raises(SystemExit) as exc_info:
                main()

        assert exc_info.value.code == 1

    def test_exits_one_on_initialization_error(self) -> None:
        """Exit code 1 when repository initialization raises an exception."""
        from scripts.check_notification_health import main

        with (
            patch(ARGV_PATH, DEFAULT_ARGV),
            patch(
                NOTIFICATION_REPO_PATH,
                side_effect=RuntimeError("DB unavailable"),
            ),
        ):
            with pytest.raises(SystemExit) as exc_info:
                main()

        assert exc_info.value.code == 1

    def test_exits_zero_when_failure_rate_exactly_at_threshold(self) -> None:
        """Exit code 0 when failure rate equals threshold (not exceeds)."""
        from scripts.check_notification_health import main

        with (
            patch(
                ARGV_PATH,
                [*DEFAULT_ARGV, "--failure-threshold", "10"],
            ),
            patch(NOTIFICATION_REPO_PATH),
            patch(
                METRICS_PATH,
                return_value=_make_metrics(failure_rate=10.0),
            ),
        ):
            with pytest.raises(SystemExit) as exc_info:
                main()

        assert exc_info.value.code == 0


class TestAlertLogic:
    """Alert conditions are evaluated against configurable thresholds."""

    def test_no_alert_below_failure_threshold(self) -> None:
        """Failure rate below threshold does not trigger an alert exit."""
        from scripts.check_notification_health import main

        with (
            patch(
                ARGV_PATH,
                [*DEFAULT_ARGV, "--failure-threshold", "20"],
            ),
            patch(NOTIFICATION_REPO_PATH),
            patch(
                METRICS_PATH,
                return_value=_make_metrics(failure_rate=5.0),
            ),
        ):
            with pytest.raises(SystemExit) as exc_info:
                main()

        assert exc_info.value.code == 0

    def test_alert_at_failure_threshold_exceeded(self) -> None:
        """Failure rate strictly above threshold triggers alert exit."""
        from scripts.check_notification_health import main

        with (
            patch(
                ARGV_PATH,
                [*DEFAULT_ARGV, "--failure-threshold", "10"],
            ),
            patch(NOTIFICATION_REPO_PATH),
            patch(
                METRICS_PATH,
                return_value=_make_metrics(failure_rate=11.0),
            ),
        ):
            with pytest.raises(SystemExit) as exc_info:
                main()

        assert exc_info.value.code == 1

    def test_custom_threshold_applied(self) -> None:
        """Custom --failure-threshold is used instead of the default 10."""
        from scripts.check_notification_health import main

        with (
            patch(
                ARGV_PATH,
                [*DEFAULT_ARGV, "--failure-threshold", "50"],
            ),
            patch(NOTIFICATION_REPO_PATH),
            patch(
                METRICS_PATH,
                return_value=_make_metrics(failure_rate=49.0),
            ),
        ):
            with pytest.raises(SystemExit) as exc_info:
                main()

        assert exc_info.value.code == 0

    def test_stuck_alert_independent_of_failure_rate(self) -> None:
        """Stuck notification alert fires even when failure rate is healthy."""
        from scripts.check_notification_health import main

        with (
            patch(ARGV_PATH, DEFAULT_ARGV),
            patch(NOTIFICATION_REPO_PATH),
            patch(
                METRICS_PATH,
                return_value=_make_metrics(failure_rate=0.0, stuck_count=1),
            ),
        ):
            with pytest.raises(SystemExit) as exc_info:
                main()

        assert exc_info.value.code == 1

    def test_no_alert_when_stuck_count_is_zero(self) -> None:
        """Zero stuck notifications does not trigger a stuck alert."""
        from scripts.check_notification_health import main

        with (
            patch(ARGV_PATH, DEFAULT_ARGV),
            patch(NOTIFICATION_REPO_PATH),
            patch(
                METRICS_PATH,
                return_value=_make_metrics(stuck_count=0),
            ),
        ):
            with pytest.raises(SystemExit) as exc_info:
                main()

        assert exc_info.value.code == 0


class TestLogging:
    """Script emits structured log messages for monitoring systems."""

    def test_logs_health_summary(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Health summary fields appear in the log output."""
        from scripts.check_notification_health import main

        with (
            patch(ARGV_PATH, DEFAULT_ARGV),
            patch(NOTIFICATION_REPO_PATH),
            patch(
                METRICS_PATH,
                return_value=_make_metrics(sent=5, failed=1),
            ),
        ):
            with caplog.at_level(logging.INFO, logger=SCRIPT_MODULE):
                with pytest.raises(SystemExit):
                    main()

        assert "sent" in caplog.text

    def test_logs_alert_when_failure_rate_exceeded(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        """An alert is logged when failure rate threshold is exceeded."""
        from scripts.check_notification_health import main

        with (
            patch(ARGV_PATH, DEFAULT_ARGV),
            patch(NOTIFICATION_REPO_PATH),
            patch(
                METRICS_PATH,
                return_value=_make_metrics(failure_rate=50.0),
            ),
        ):
            with caplog.at_level(logging.WARNING, logger=SCRIPT_MODULE):
                with pytest.raises(SystemExit):
                    main()

        assert any(r.levelno >= logging.WARNING for r in caplog.records)

    def test_logs_timestamp_in_summary(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Log output contains the timestamp from the health summary."""
        from scripts.check_notification_health import main

        ts = "2026-03-20T00:00:00+00:00"
        with (
            patch(ARGV_PATH, DEFAULT_ARGV),
            patch(NOTIFICATION_REPO_PATH),
            patch(
                METRICS_PATH,
                return_value=_make_metrics(timestamp=ts),
            ),
        ):
            with caplog.at_level(logging.INFO, logger=SCRIPT_MODULE):
                with pytest.raises(SystemExit):
                    main()

        assert ts in caplog.text

    def test_logs_stuck_alert_message(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        """A warning is logged when stuck notifications are detected."""
        from scripts.check_notification_health import main

        with (
            patch(ARGV_PATH, DEFAULT_ARGV),
            patch(NOTIFICATION_REPO_PATH),
            patch(
                METRICS_PATH,
                return_value=_make_metrics(stuck_count=3),
            ),
        ):
            with caplog.at_level(logging.WARNING, logger=SCRIPT_MODULE):
                with pytest.raises(SystemExit):
                    main()

        assert any(r.levelno >= logging.WARNING for r in caplog.records)

    def test_logs_initialization_error_without_details(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Initialization errors are logged without sensitive details."""
        from scripts.check_notification_health import main

        secret = "DB_PASSWORD=hunter2"
        with (
            patch(ARGV_PATH, DEFAULT_ARGV),
            patch(
                NOTIFICATION_REPO_PATH,
                side_effect=RuntimeError(secret),
            ),
        ):
            with caplog.at_level(logging.DEBUG, logger=SCRIPT_MODULE):
                with pytest.raises(SystemExit):
                    main()

        assert secret not in caplog.text


class TestDependencyInitialization:
    """Repository and metrics are constructed correctly."""

    def test_notification_repository_is_instantiated(self) -> None:
        """NotificationRepository is created during script startup."""
        from scripts.check_notification_health import main

        mock_repo_cls = MagicMock()
        with (
            patch(ARGV_PATH, DEFAULT_ARGV),
            patch(NOTIFICATION_REPO_PATH, mock_repo_cls),
            patch(METRICS_PATH, return_value=_make_metrics()),
        ):
            with pytest.raises(SystemExit):
                main()

        mock_repo_cls.assert_called_once()

    def test_metrics_instantiated_with_repository(self) -> None:
        """NotificationMetrics receives the repository instance."""
        from scripts.check_notification_health import main

        mock_repo_instance = MagicMock()
        mock_repo_cls = MagicMock(return_value=mock_repo_instance)
        mock_metrics_cls = MagicMock(return_value=_make_metrics())

        with (
            patch(ARGV_PATH, DEFAULT_ARGV),
            patch(NOTIFICATION_REPO_PATH, mock_repo_cls),
            patch(METRICS_PATH, mock_metrics_cls),
        ):
            with pytest.raises(SystemExit):
                main()

        mock_metrics_cls.assert_called_once_with(mock_repo_instance)

    def test_catches_repository_init_error(self) -> None:
        """Script handles repository construction failure gracefully."""
        from scripts.check_notification_health import main

        with (
            patch(ARGV_PATH, DEFAULT_ARGV),
            patch(
                NOTIFICATION_REPO_PATH,
                side_effect=Exception("connection refused"),
            ),
        ):
            with pytest.raises(SystemExit) as exc_info:
                main()

        assert exc_info.value.code == 1

    def test_logs_failure_on_init_error(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        """An error-level log is emitted when initialization fails."""
        from scripts.check_notification_health import main

        with (
            patch(ARGV_PATH, DEFAULT_ARGV),
            patch(
                NOTIFICATION_REPO_PATH,
                side_effect=Exception("connection refused"),
            ),
        ):
            with caplog.at_level(logging.ERROR, logger=SCRIPT_MODULE):
                with pytest.raises(SystemExit):
                    main()

        assert any(r.levelno >= logging.ERROR for r in caplog.records)
