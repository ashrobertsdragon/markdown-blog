"""Unit tests for ErrorLogger and ErrorEntry.

Tests cover ErrorEntry model construction, log_error() behaviour including
thread safety and deque overflow, get_recent_errors() ordering and isolation,
clear() correctness, and edge cases for unicode, empty strings, and boundary
counts.
"""

import threading
from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock


from backend.infrastructure.monitoring.error_logger import (
    ErrorEntry,
    ErrorLogger,
)


class TestErrorEntry:
    """ErrorEntry Pydantic model construction and serialisation."""

    def test_creates_with_all_fields(self) -> None:
        """All four fields are set correctly when provided."""
        ts = datetime.now(UTC)
        entry = ErrorEntry(
            timestamp=ts,
            message="boom",
            stack_trace="Traceback...",
            endpoint="/api/posts",
        )
        assert entry.timestamp == ts
        assert entry.message == "boom"
        assert entry.stack_trace == "Traceback..."
        assert entry.endpoint == "/api/posts"

    def test_endpoint_defaults_to_none(self) -> None:
        """endpoint is None when not provided."""
        entry = ErrorEntry(
            timestamp=datetime.now(UTC),
            message="x",
            stack_trace="tb",
        )
        assert entry.endpoint is None

    def test_model_dump_json_serialises_without_error(self) -> None:
        """model_dump_json() produces valid JSON without raising."""
        entry = ErrorEntry(
            timestamp=datetime.now(UTC),
            message="serialise me",
            stack_trace="tb",
            endpoint="/health",
        )
        result = entry.model_dump_json()
        assert isinstance(result, str)
        assert len(result) > 0

    def test_timestamp_field_accepts_datetime_objects(self) -> None:
        """timestamp accepts any datetime object including UTC-aware ones."""
        ts = datetime(2024, 6, 15, 12, 0, 0, tzinfo=UTC)
        entry = ErrorEntry(timestamp=ts, message="m", stack_trace="tb")
        assert entry.timestamp == ts


class TestLogError:
    """log_error() creates, stores, and returns ErrorEntry instances."""

    def test_returns_error_entry_instance(
        self, clear_error_logger_after_test: None
    ) -> None:
        """log_error returns an ErrorEntry."""
        result = ErrorLogger.log_error("msg", "tb")
        assert isinstance(result, ErrorEntry)

    def test_stored_entry_has_correct_message(
        self, clear_error_logger_after_test: None
    ) -> None:
        """Stored entry carries the supplied message."""
        ErrorLogger.log_error("hello world", "tb")
        errors = ErrorLogger.get_recent_errors()
        assert errors[0].message == "hello world"

    def test_stored_entry_has_correct_stack_trace(
        self, clear_error_logger_after_test: None
    ) -> None:
        """Stored entry carries the supplied stack_trace."""
        ErrorLogger.log_error("msg", "line 1\nline 2")
        errors = ErrorLogger.get_recent_errors()
        assert errors[0].stack_trace == "line 1\nline 2"

    def test_stored_entry_has_correct_endpoint(
        self, clear_error_logger_after_test: None
    ) -> None:
        """Stored entry carries the supplied endpoint."""
        ErrorLogger.log_error("msg", "tb", endpoint="/api/comments")
        errors = ErrorLogger.get_recent_errors()
        assert errors[0].endpoint == "/api/comments"

    def test_auto_sets_timestamp_close_to_now(
        self, clear_error_logger_after_test: None
    ) -> None:
        """auto-set timestamp is within two seconds of the call time."""
        before = datetime.now(UTC)
        ErrorLogger.log_error("ts test", "tb")
        after = datetime.now(UTC)
        errors = ErrorLogger.get_recent_errors()
        assert before <= errors[0].timestamp <= after + timedelta(seconds=2)

    def test_calls_python_logger(
        self, clear_error_logger_after_test: None, mock_logger: MagicMock
    ) -> None:
        """log_error delegates to the module-level Python logger."""
        ErrorLogger.log_error("logged msg", "tb")
        assert (
            mock_logger.error.called
            or mock_logger.exception.called
            or mock_logger.warning.called
            or mock_logger.info.called
            or mock_logger.debug.called
            or mock_logger.log.called
        )

    def test_concurrent_writes_all_stored(
        self, clear_error_logger_after_test: None
    ) -> None:
        """10 concurrent log_error calls all produce stored entries."""
        errors_logged: list[Exception] = []

        def worker(index: int) -> None:
            try:
                ErrorLogger.log_error(f"concurrent-{index}", "tb")
            except Exception as exc:  # noqa: BLE001
                errors_logged.append(exc)

        threads = [
            threading.Thread(target=worker, args=(i,)) for i in range(10)
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert errors_logged == []
        assert len(ErrorLogger.get_recent_errors()) == 10

    def test_enforces_maxlen_50_after_51_entries(
        self, clear_error_logger_after_test: None
    ) -> None:
        """After 51 log_error calls the deque holds exactly 50 entries."""
        for i in range(51):
            ErrorLogger.log_error(f"msg-{i}", "tb")
        assert len(ErrorLogger.get_recent_errors()) == 50

    def test_long_stack_trace_stored_intact(
        self, clear_error_logger_after_test: None
    ) -> None:
        """A 10 KB stack trace is stored without truncation."""
        long_tb = "x" * 10_240
        ErrorLogger.log_error("long", long_tb)
        errors = ErrorLogger.get_recent_errors()
        assert errors[0].stack_trace == long_tb

    def test_special_characters_in_message_stored_correctly(
        self, clear_error_logger_after_test: None
    ) -> None:
        """Messages with special/unicode characters are preserved verbatim."""
        special = "Error: <tag> & 'quote' \n\t\\backslash"
        ErrorLogger.log_error(special, "tb")
        errors = ErrorLogger.get_recent_errors()
        assert errors[0].message == special

    def test_empty_message_stored_correctly(
        self, clear_error_logger_after_test: None
    ) -> None:
        """An empty message string is stored as-is."""
        ErrorLogger.log_error("", "tb")
        errors = ErrorLogger.get_recent_errors()
        assert errors[0].message == ""


class TestGetRecentErrors:
    """get_recent_errors() ordering, limiting, and copy semantics."""

    def test_returns_list_type(
        self, clear_error_logger_after_test: None
    ) -> None:
        """Return type is always list."""
        result = ErrorLogger.get_recent_errors()
        assert isinstance(result, list)

    def test_returns_empty_list_when_no_errors(
        self, clear_error_logger_after_test: None
    ) -> None:
        """Returns [] when no errors have been logged."""
        assert ErrorLogger.get_recent_errors() == []

    def test_returns_newest_first_order(
        self, clear_error_logger_after_test: None
    ) -> None:
        """Entries are returned newest-first (reverse insertion order)."""
        ErrorLogger.log_error("first", "tb")
        ErrorLogger.log_error("second", "tb")
        ErrorLogger.log_error("third", "tb")
        errors = ErrorLogger.get_recent_errors()
        assert errors[0].message == "third"
        assert errors[1].message == "second"
        assert errors[2].message == "first"

    def test_limit_none_returns_all_entries(
        self, clear_error_logger_after_test: None
    ) -> None:
        """limit=None returns all stored entries."""
        for i in range(7):
            ErrorLogger.log_error(f"msg-{i}", "tb")
        assert len(ErrorLogger.get_recent_errors(limit=None)) == 7

    def test_limit_5_returns_5_newest(
        self, clear_error_logger_after_test: None
    ) -> None:
        """limit=5 returns exactly the 5 most recent entries."""
        for i in range(10):
            ErrorLogger.log_error(f"msg-{i}", "tb")
        result = ErrorLogger.get_recent_errors(limit=5)
        assert len(result) == 5
        assert result[0].message == "msg-9"

    def test_returns_independent_copy(
        self, clear_error_logger_after_test: None
    ) -> None:
        """Mutating the returned list does not affect internal state."""
        ErrorLogger.log_error("original", "tb")
        copy = ErrorLogger.get_recent_errors()
        copy.clear()
        assert len(ErrorLogger.get_recent_errors()) == 1

    def test_concurrent_reads_and_writes_no_exception(
        self, clear_error_logger_after_test: None
    ) -> None:
        """5 readers and 5 writers running concurrently raise no exceptions."""
        exceptions: list[Exception] = []

        def writer(index: int) -> None:
            try:
                ErrorLogger.log_error(f"write-{index}", "tb")
            except Exception as exc:  # noqa: BLE001
                exceptions.append(exc)

        def reader() -> None:
            try:
                ErrorLogger.get_recent_errors()
            except Exception as exc:  # noqa: BLE001
                exceptions.append(exc)

        threads: list[threading.Thread] = [
            threading.Thread(target=writer, args=(i,)) for i in range(5)
        ] + [threading.Thread(target=reader) for _ in range(5)]

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert exceptions == []


class TestClear:
    """clear() removes all entries from the deque."""

    def test_clear_removes_all_entries(
        self, clear_error_logger_after_test: None
    ) -> None:
        """After 5 logs, clear() empties the deque."""
        for i in range(5):
            ErrorLogger.log_error(f"msg-{i}", "tb")
        ErrorLogger.clear()
        assert len(ErrorLogger.get_recent_errors()) == 0

    def test_get_recent_errors_returns_empty_after_clear(
        self, clear_error_logger_after_test: None
    ) -> None:
        """get_recent_errors() returns [] immediately after clear()."""
        ErrorLogger.log_error("before clear", "tb")
        ErrorLogger.clear()
        assert ErrorLogger.get_recent_errors() == []

    def test_logging_after_clear_works(
        self, clear_error_logger_after_test: None
    ) -> None:
        """New entries are stored correctly after a clear()."""
        ErrorLogger.log_error("pre-clear", "tb")
        ErrorLogger.clear()
        ErrorLogger.log_error("post-clear", "tb")
        errors = ErrorLogger.get_recent_errors()
        assert len(errors) == 1
        assert errors[0].message == "post-clear"


class TestEdgeCases:
    """Edge cases: boundary counts, FIFO overflow, unicode, explicit None."""

    def test_exactly_50_entries_deque_has_50(
        self, clear_error_logger_after_test: None
    ) -> None:
        """Logging exactly 50 errors leaves the deque at exactly 50."""
        for i in range(50):
            ErrorLogger.log_error(f"msg-{i}", "tb")
        assert len(ErrorLogger.get_recent_errors()) == 50

    def test_51st_entry_oldest_removed(
        self, clear_error_logger_after_test: None
    ) -> None:
        """The 51st entry triggers removal of the oldest; count stays at 50."""
        for i in range(51):
            ErrorLogger.log_error(f"msg-{i}", "tb")
        errors = ErrorLogger.get_recent_errors()
        assert len(errors) == 50
        assert errors[0].message == "msg-50"

    def test_fifo_overflow_first_added_is_removed(
        self, clear_error_logger_after_test: None
    ) -> None:
        """The very first-added entry is the one evicted on overflow."""
        ErrorLogger.log_error("first-ever", "tb")
        for i in range(50):
            ErrorLogger.log_error(f"filler-{i}", "tb")
        messages = {e.message for e in ErrorLogger.get_recent_errors()}
        assert "first-ever" not in messages

    def test_unicode_emoji_in_message_stored_correctly(
        self, clear_error_logger_after_test: None
    ) -> None:
        """Emoji and multi-byte unicode in message are preserved verbatim."""
        msg = "Error 💥 — naïve résumé 中文"
        ErrorLogger.log_error(msg, "tb")
        errors = ErrorLogger.get_recent_errors()
        assert errors[0].message == msg

    def test_explicit_none_endpoint_stored_as_none_not_string(
        self, clear_error_logger_after_test: None
    ) -> None:
        """Passing endpoint=None explicitly stores None, not the string 'None'."""
        ErrorLogger.log_error("msg", "tb", endpoint=None)
        errors = ErrorLogger.get_recent_errors()
        assert errors[0].endpoint is None
        assert errors[0].endpoint != "None"
