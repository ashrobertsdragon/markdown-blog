"""Error logging infrastructure for capturing and retrieving recent errors."""

import logging
import threading
from collections import deque
from datetime import UTC, datetime
from typing import ClassVar

from pydantic import BaseModel

logger = logging.getLogger(__name__)

_MAX_ERRORS = 50


class ErrorEntry(BaseModel):
    """A single captured error event.

    Attributes:
        timestamp: When the error occurred (timezone-aware UTC).
        message: Human-readable error description.
        stack_trace: Full traceback or exception detail.
        endpoint: Optional HTTP endpoint where the error originated.
    """

    timestamp: datetime
    message: str
    stack_trace: str
    endpoint: str | None = None


class ErrorLogger:
    """In-memory ring buffer for recent application errors.

    Stores up to _MAX_ERRORS entries using a thread-safe deque. All class
    methods acquire an RLock around deque mutations; the Python logger call is
    intentionally performed outside the lock to avoid I/O inside a critical
    section.
    """

    _errors: ClassVar[deque[ErrorEntry]] = deque(maxlen=_MAX_ERRORS)
    _lock: ClassVar[threading.RLock] = threading.RLock()

    @classmethod
    def log_error(
        cls,
        message: str,
        stack_trace: str,
        endpoint: str | None = None,
    ) -> ErrorEntry:
        """Record an error and return the stored entry.

        Args:
            message: Human-readable error description.
            stack_trace: Full traceback or exception detail.
            endpoint: Optional HTTP endpoint where the error originated.

        Returns:
            The ErrorEntry that was appended to the internal deque.
        """
        entry = ErrorEntry(
            timestamp=datetime.now(UTC),
            message=message,
            stack_trace=stack_trace,
            endpoint=endpoint,
        )
        with cls._lock:
            cls._errors.append(entry)
        safe_message = message.replace("\n", "\\n").replace("\r", "\\r")
        safe_endpoint = (
            endpoint.replace("\n", "\\n").replace("\r", "\\r")
            if endpoint is not None
            else endpoint
        )
        logger.debug(
            "Error captured: %s (endpoint=%s)", safe_message, safe_endpoint
        )
        return entry

    @classmethod
    def get_recent_errors(cls, limit: int | None = None) -> list[ErrorEntry]:
        """Return a snapshot of recent errors, newest first.

        Args:
            limit: Maximum number of entries to return. ``None`` returns all.

        Returns:
            An independent list (modifying it does not affect internal state).
        """
        with cls._lock:
            snapshot = list(cls._errors)
        snapshot.reverse()
        if limit is not None:
            return snapshot[:limit]
        return snapshot

    @classmethod
    def clear(cls) -> None:
        """Remove all entries from the internal deque.

        Idempotent and thread-safe.
        """
        with cls._lock:
            cls._errors.clear()
