"""Unit tests for GetNotificationHistoryQuery.

Covers:
- Valid instantiation with user_id, skip, limit
- user_id <= 0 raises ValueError
- skip < 0 raises ValueError
- limit < 1 raises ValueError
- limit > 100 raises ValueError
"""

import pytest

from backend.application.queries.get_notification_history_query import (
    GetNotificationHistoryQuery,
)


def _make(
    *,
    user_id: int = 1,
    skip: int = 0,
    limit: int = 50,
) -> GetNotificationHistoryQuery:
    """Build a valid GetNotificationHistoryQuery."""
    return GetNotificationHistoryQuery(
        user_id=user_id,
        skip=skip,
        limit=limit,
    )


def test_valid_query_instantiates() -> None:
    """Valid fields produce a query with correct attribute values."""
    query = _make(user_id=1, skip=0, limit=50)

    assert query.user_id == 1
    assert query.skip == 0
    assert query.limit == 50


def test_rejects_zero_user_id() -> None:
    """user_id=0 raises ValueError."""
    with pytest.raises(ValueError, match="user_id"):
        _make(user_id=0)


def test_rejects_negative_user_id() -> None:
    """Negative user_id raises ValueError."""
    with pytest.raises(ValueError, match="user_id"):
        _make(user_id=-1)


def test_rejects_negative_skip() -> None:
    """Negative skip raises ValueError."""
    with pytest.raises(ValueError, match="skip"):
        _make(skip=-1)


def test_accepts_zero_skip() -> None:
    """skip=0 is valid (first page)."""
    query = _make(skip=0)

    assert query.skip == 0


def test_rejects_zero_limit() -> None:
    """limit=0 raises ValueError."""
    with pytest.raises(ValueError, match="limit"):
        _make(limit=0)


def test_rejects_negative_limit() -> None:
    """Negative limit raises ValueError."""
    with pytest.raises(ValueError, match="limit"):
        _make(limit=-5)


def test_rejects_limit_over_100() -> None:
    """limit > 100 raises ValueError."""
    with pytest.raises(ValueError, match="limit"):
        _make(limit=101)


def test_accepts_limit_of_100() -> None:
    """limit=100 is the maximum valid value."""
    query = _make(limit=100)

    assert query.limit == 100


def test_accepts_limit_of_1() -> None:
    """limit=1 is the minimum valid value."""
    query = _make(limit=1)

    assert query.limit == 1
