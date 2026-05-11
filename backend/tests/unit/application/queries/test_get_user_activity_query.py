"""Unit tests for GetUserActivityQuery and UserActivity dataclasses.

Test Coverage:
- Query creation and field storage (1 test)
- UserActivity dataclass field storage (1 test)
- Frozen dataclass immutability (1 test)

Total: 3 unit tests
"""

import pytest

from backend.application.queries.get_user_activity_query import (
    GetUserActivityQuery,
    UserActivity,
)


def test_query_creation_stores_user_id() -> None:
    """Verify GetUserActivityQuery stores user_id correctly.

    The query dataclass must preserve the user_id passed at construction
    so the handler can use it to look up the correct user.
    """
    query = GetUserActivityQuery(user_id=42)

    assert query.user_id == 42


def test_user_activity_stores_all_fields() -> None:
    """Verify UserActivity stores all required activity fields.

    The response dataclass must hold last_login, posts_count,
    comments_count, recent_posts, and recent_comments so callers
    can access the complete user activity summary.
    """
    activity = UserActivity(
        last_login=None,
        posts_count=5,
        comments_count=10,
        recent_posts=[],
        recent_comments=[],
    )

    assert activity.last_login is None
    assert activity.posts_count == 5
    assert activity.comments_count == 10
    assert activity.recent_posts == []
    assert activity.recent_comments == []


def test_get_user_activity_query_is_frozen() -> None:
    """Verify GetUserActivityQuery is immutable after creation.

    The query is a value object — once constructed it must not be
    mutated. A frozen dataclass raises AttributeError (or TypeError)
    on any attempted field assignment.
    """
    query = GetUserActivityQuery(user_id=42)

    with pytest.raises((AttributeError, TypeError)):
        query.user_id = 99  # type: ignore[misc]
