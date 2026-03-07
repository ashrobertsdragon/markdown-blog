"""Unit tests for GetPostCommentsQuery."""

import pytest

from backend.application.queries.get_post_comments_query import (
    GetPostCommentsQuery,
)


def test_query_creates_with_defaults() -> None:
    """Valid post_id with defaults produces correct attribute values."""
    q = GetPostCommentsQuery(post_id=5)

    assert q.post_id == 5
    assert q.skip == 0
    assert q.limit == 50
    assert q.show_pending is False


def test_query_accepts_custom_values() -> None:
    """Custom skip, limit, and show_pending are preserved."""
    q = GetPostCommentsQuery(post_id=3, skip=10, limit=25, show_pending=True)

    assert q.skip == 10
    assert q.limit == 25
    assert q.show_pending is True


def test_query_is_frozen() -> None:
    """Query fields cannot be mutated after construction."""
    q = GetPostCommentsQuery(post_id=1)

    with pytest.raises((AttributeError, TypeError)):
        q.post_id = 99  # type: ignore[misc]


def test_query_rejects_zero_post_id() -> None:
    """post_id=0 raises ValueError."""
    with pytest.raises(ValueError, match="post_id"):
        GetPostCommentsQuery(post_id=0)


def test_query_rejects_negative_post_id() -> None:
    """Negative post_id raises ValueError."""
    with pytest.raises(ValueError, match="post_id"):
        GetPostCommentsQuery(post_id=-1)


def test_query_rejects_negative_skip() -> None:
    """Negative skip raises ValueError."""
    with pytest.raises(ValueError, match="skip"):
        GetPostCommentsQuery(post_id=1, skip=-1)


def test_query_rejects_zero_limit() -> None:
    """limit=0 raises ValueError."""
    with pytest.raises(ValueError, match="limit"):
        GetPostCommentsQuery(post_id=1, limit=0)


def test_query_rejects_limit_exceeding_100() -> None:
    """limit > 100 raises ValueError."""
    with pytest.raises(ValueError, match="limit"):
        GetPostCommentsQuery(post_id=1, limit=101)


def test_query_accepts_limit_boundaries() -> None:
    """Limit of 1 and 100 are both valid."""
    assert GetPostCommentsQuery(post_id=1, limit=1).limit == 1
    assert GetPostCommentsQuery(post_id=1, limit=100).limit == 100


def test_query_equality() -> None:
    """Two queries with identical fields are equal."""
    a = GetPostCommentsQuery(post_id=1, skip=5, limit=10)
    b = GetPostCommentsQuery(post_id=1, skip=5, limit=10)

    assert a == b
