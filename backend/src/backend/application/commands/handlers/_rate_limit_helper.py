"""Shared rate-limit enforcement for comment submission handlers."""

import time

from backend.exceptions import RateLimitExceededError
from backend.infrastructure.moderation.rate_limit_service import (
    RateLimitService,
)


def enforce_rate_limit(
    identifier: str,
    ip: str,
    is_admin: bool,
    rate_limit_service: RateLimitService,
) -> None:
    """Check the sliding-window rate limit and raise if exhausted.

    Args:
        identifier: Unique key for the requester (e.g. ``"user:42"``).
        ip: Remote IP address of the requester.
        is_admin: When True the rate limit check is bypassed.
        rate_limit_service: Service that tracks submission timestamps.

    Raises:
        RateLimitExceededError: If the per-user window is full.
    """
    allowed = rate_limit_service.check_limit(
        identifier=identifier,
        ip=ip,
        is_admin=is_admin,
    )
    if not allowed:
        reset_timestamp = rate_limit_service.get_reset_time(identifier)
        reset_after = max(1, int(reset_timestamp - time.time()))
        raise RateLimitExceededError(
            f"Too many comments. Please wait {reset_after} seconds.",
            reset_after=reset_after,
            remaining=0,
        )
