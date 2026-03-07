"""Unit tests for RateLimitService."""

import time

from freezegun import freeze_time

from backend.infrastructure.moderation.rate_limit_service import (
    RateLimitService,
)


class TestCheckLimit:
    """Tests for the core check_limit method."""

    def test_rate_limit_allows_first_comment(self) -> None:
        """First request from any identifier is always allowed."""
        service = RateLimitService()
        assert service.check_limit("user:1", "127.0.0.1") is True

    def test_rate_limit_allows_up_to_five_comments(self) -> None:
        """Five requests are permitted; the sixth is denied."""
        service = RateLimitService()
        for _ in range(5):
            result = service.check_limit("user:2", "127.0.0.1")
            assert result is True
        sixth = service.check_limit("user:2", "127.0.0.1")
        assert sixth is False

    @freeze_time("2026-01-01 00:00:00")
    def test_rate_limit_resets_after_window_expires(self) -> None:
        """Counter resets after the 60-second window elapses."""
        service = RateLimitService()
        for _ in range(5):
            service.check_limit("user:3", "127.0.0.1")
        assert service.check_limit("user:3", "127.0.0.1") is False

        with freeze_time("2026-01-01 00:01:01"):
            assert service.check_limit("user:3", "127.0.0.1") is True

    def test_admin_users_bypass_rate_limits(self) -> None:
        """Admin flag causes check_limit to return True regardless of count."""
        service = RateLimitService()
        for _ in range(10):
            result = service.check_limit("user:4", "127.0.0.1", is_admin=True)
            assert result is True

    def test_anonymous_users_rate_limited_by_ip(self) -> None:
        """Empty user identifier falls back to an IP-keyed bucket."""
        service = RateLimitService()
        for _ in range(5):
            service.check_limit("", "192.168.1.1")
        assert service.check_limit("", "192.168.1.1") is False

    def test_different_users_have_independent_limits(self) -> None:
        """Distinct identifiers do not share rate limit counters."""
        service = RateLimitService()
        for _ in range(5):
            service.check_limit("user:10", "10.0.0.1")
        assert service.check_limit("user:10", "10.0.0.1") is False
        assert service.check_limit("user:11", "10.0.0.1") is True


class TestGetRemaining:
    """Tests for the get_remaining method."""

    def test_get_remaining_returns_correct_count(self) -> None:
        """Remaining count decrements accurately down to zero."""
        service = RateLimitService()
        assert service.get_remaining("user:20") == 5
        service.check_limit("user:20", "127.0.0.1")
        assert service.get_remaining("user:20") == 4
        service.check_limit("user:20", "127.0.0.1")
        assert service.get_remaining("user:20") == 3
        service.check_limit("user:20", "127.0.0.1")
        assert service.get_remaining("user:20") == 2
        service.check_limit("user:20", "127.0.0.1")
        assert service.get_remaining("user:20") == 1
        service.check_limit("user:20", "127.0.0.1")
        assert service.get_remaining("user:20") == 0


class TestGetResetTime:
    """Tests for the get_reset_time method."""

    @freeze_time("2026-01-01 12:00:00")
    def test_get_reset_time_returns_unix_timestamp(self) -> None:
        """Reset time is a future Unix timestamp after the first submission."""
        service = RateLimitService()
        service.check_limit("user:30", "127.0.0.1")
        reset = service.get_reset_time("user:30")
        assert isinstance(reset, int)
        now = int(time.time())
        assert reset > now


class TestCacheCleanup:
    """Tests for internal cache hygiene."""

    @freeze_time("2026-01-01 00:00:00")
    def test_cache_cleanup_prevents_memory_leak(self) -> None:
        """Expired entries are purged from _cache on subsequent requests."""
        service = RateLimitService()
        with freeze_time("2026-01-01 00:00:00"):
            for i in range(100):
                service.check_limit(f"user:{i}", f"10.0.0.{i % 256}")

        with freeze_time("2026-01-01 00:02:00"):
            service.check_limit("user:999", "10.0.0.1")
            assert len(service._cache) < 100  # noqa: SLF001


class TestPerformance:
    """Performance baseline tests for the rate limit service."""

    def test_rate_limit_check_completes_under_50ms(self) -> None:
        """A single check_limit call resolves in under 50 milliseconds."""
        service = RateLimitService()
        start = time.perf_counter()
        service.check_limit("user:perf", "127.0.0.1")
        elapsed_ms = (time.perf_counter() - start) * 1000
        assert elapsed_ms < 50
