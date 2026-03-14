"""Rate limiting service for comment submissions."""

import threading
import time


class RateLimitService:
    """In-memory sliding window rate limiter.

    Tracks submission timestamps per identifier in a thread-safe cache.
    Expired entries are pruned automatically to prevent unbounded memory growth.
    """

    _cache: dict[str, list[float]]
    _lock: threading.RLock
    _window_seconds: int
    _max_per_window: int
    _request_count: int
    _last_cleanup: float

    def __init__(
        self, window_seconds: int = 60, max_per_window: int = 5
    ) -> None:
        """Initialise the rate limit service.

        Args:
            window_seconds: Rolling window duration in seconds.
            max_per_window: Maximum allowed submissions within the window.
        """
        self._window_seconds = window_seconds
        self._max_per_window = max_per_window
        self._cache = {}
        self._lock = threading.RLock()
        self._request_count = 0
        self._last_cleanup = time.time()

    def check_limit(
        self, identifier: str, ip: str, is_admin: bool = False
    ) -> bool:
        """Check whether the requester is within the rate limit.

        Admins always pass. Empty identifiers are keyed by IP address.
        Records a timestamp for each allowed submission.

        Args:
            identifier: User identifier (e.g. ``"user:1"``).
            ip: Remote IP address used as fallback key when identifier is empty.
            is_admin: When ``True``, bypasses all rate limit checks.

        Returns:
            ``True`` if the submission is permitted, ``False`` if the limit is
            exceeded.
        """
        if is_admin:
            return True

        key = identifier if identifier else f"ip:{ip}"

        with self._lock:
            self._request_count += 1
            self._maybe_cleanup()

            now = time.time()
            cutoff = now - self._window_seconds
            timestamps = self._cache.get(key, [])
            valid = [t for t in timestamps if t > cutoff]

            if len(valid) >= self._max_per_window:
                self._cache[key] = valid
                return False

            valid.append(now)
            self._cache[key] = valid
            return True

    def get_remaining(self, identifier: str) -> int:
        """Return the number of submissions remaining in the current window.

        Args:
            identifier: Cache key as stored — either ``"user:{id}"`` or
                ``"ip:{addr}"`` (the key that check_limit resolved to).

        Returns:
            Remaining submission count, between ``0`` and ``max_per_window``.
        """
        with self._lock:
            now = time.time()
            cutoff = now - self._window_seconds
            timestamps = self._cache.get(identifier, [])
            valid_count = sum(1 for t in timestamps if t > cutoff)
            return max(0, self._max_per_window - valid_count)

    def get_reset_time(self, identifier: str) -> int:
        """Return the Unix timestamp when the oldest window entry expires.

        Args:
            identifier: Cache key as stored — either ``"user:{id}"`` or
                ``"ip:{addr}"`` (the key that check_limit resolved to).

        Returns:
            Unix timestamp (integer) at which the oldest in-window entry
            expires, or the current time if no entries exist.
        """
        with self._lock:
            now = time.time()
            cutoff = now - self._window_seconds
            timestamps = self._cache.get(identifier, [])
            valid = [t for t in timestamps if t > cutoff]

            if not valid:
                return int(now)

            return int(min(valid) + self._window_seconds)

    def clear(self) -> None:
        """Remove all rate limit entries from the cache.

        Intended for test environments to reset state between test runs.
        """
        with self._lock:
            self._cache.clear()

    def _cleanup_expired_entries(self) -> None:
        """Remove cache entries whose entire timestamp list has expired.

        Iterates the cache and drops any key whose sliding window is empty.
        """
        now = time.time()
        cutoff = now - self._window_seconds
        expired_keys = [
            key
            for key, timestamps in self._cache.items()
            if not any(t > cutoff for t in timestamps)
        ]
        for key in expired_keys:
            del self._cache[key]

    def _maybe_cleanup(self) -> None:
        """Trigger cleanup when request count or time threshold is reached.

        Runs every 100 requests or when more than ``window_seconds`` seconds
        have elapsed since the last cleanup.
        """
        now = time.time()
        if (
            self._request_count % 100 == 0
            or now - self._last_cleanup > self._window_seconds
        ):
            self._cleanup_expired_entries()
            self._last_cleanup = now
