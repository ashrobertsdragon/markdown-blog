"""Unit tests for get_user_activity_query_handler.

Test Coverage:
- Return structure validation (1 test)
- User not found error handling (2 tests)
- posts_count and comments_count aggregation (2 tests)
- Recent posts limit=5, recent comments limit=10 (2 tests)
- Zero-activity user (1 test)
- Post and comment aggregate preservation (2 tests)
- last_login is None (1 test)

Total: 11 unit tests
"""

from datetime import UTC, datetime
from unittest.mock import Mock

import pytest

from backend.application.queries.get_user_activity_query import (
    GetUserActivityQuery,
    UserActivity,
)
from backend.application.queries.handlers.get_user_activity_query_handler import (
    get_user_activity_query_handler,
)


@pytest.fixture
def mock_user() -> Mock:
    """Fixture providing a mock User with id=42."""
    user = Mock()
    user.id = 42
    return user


@pytest.fixture
def mock_post() -> Mock:
    """Fixture providing a mock Post aggregate."""
    post = Mock()
    post.id = 1
    post.title = "Test Post"
    post.author_id = 42
    post.published_at = datetime(2025, 1, 10, tzinfo=UTC)
    return post


@pytest.fixture
def mock_comment() -> Mock:
    """Fixture providing a mock Comment aggregate."""
    comment = Mock()
    comment.id = 1
    comment.post_id = 10
    comment.author_id = 42
    comment.created_at = datetime(2025, 1, 15, tzinfo=UTC)
    return comment


@pytest.fixture
def mock_user_repo(mock_user: Mock) -> Mock:
    """Fixture providing a mock UserRepository returning mock_user by default."""
    repo = Mock()
    repo.find_by_id.return_value = mock_user
    return repo


@pytest.fixture
def mock_post_repo(mock_post: Mock) -> Mock:
    """Fixture providing a mock PostRepository."""
    repo = Mock()
    repo.find_by_author.return_value = [mock_post]
    repo.count_by_author.return_value = 3
    return repo


@pytest.fixture
def mock_comment_repo(mock_comment: Mock) -> Mock:
    """Fixture providing a mock CommentRepository."""
    repo = Mock()
    repo.find_by_author.return_value = [mock_comment]
    repo.count_by_author.return_value = 7
    return repo


def test_handler_returns_user_activity_structure(
    mock_user_repo: Mock,
    mock_post_repo: Mock,
    mock_comment_repo: Mock,
) -> None:
    """Verify handler returns a UserActivity with all required fields.

    The handler must produce a UserActivity instance that has last_login,
    posts_count, comments_count, recent_posts, and recent_comments so
    callers can access the full activity summary without further processing.
    """
    query = GetUserActivityQuery(user_id=42)

    result = get_user_activity_query_handler(
        query=query,
        user_repo=mock_user_repo,
        post_repo=mock_post_repo,
        comment_repo=mock_comment_repo,
    )

    assert isinstance(result, UserActivity)
    assert hasattr(result, "last_login")
    assert hasattr(result, "posts_count")
    assert hasattr(result, "comments_count")
    assert hasattr(result, "recent_posts")
    assert hasattr(result, "recent_comments")


def test_handler_raises_value_error_when_user_not_found(
    mock_post_repo: Mock,
    mock_comment_repo: Mock,
) -> None:
    """Verify handler raises ValueError when user does not exist.

    If find_by_id returns None the user is absent from the system.
    The handler must raise ValueError with a message containing
    'not found' so callers can map this to a 404 response.
    """
    user_repo = Mock()
    user_repo.find_by_id.return_value = None

    query = GetUserActivityQuery(user_id=99)

    with pytest.raises(ValueError, match="not found"):
        get_user_activity_query_handler(
            query=query,
            user_repo=user_repo,
            post_repo=mock_post_repo,
            comment_repo=mock_comment_repo,
        )


def test_handler_returns_correct_posts_count(
    mock_user_repo: Mock,
    mock_post_repo: Mock,
    mock_comment_repo: Mock,
) -> None:
    """Verify handler sets posts_count to the value from count_by_author.

    posts_count must reflect the total number of posts authored by the
    user, not just the number of recent posts returned in recent_posts.
    """
    mock_post_repo.count_by_author.return_value = 17

    query = GetUserActivityQuery(user_id=42)

    result = get_user_activity_query_handler(
        query=query,
        user_repo=mock_user_repo,
        post_repo=mock_post_repo,
        comment_repo=mock_comment_repo,
    )

    assert result.posts_count == 17
    mock_post_repo.count_by_author.assert_called_once_with(42)


def test_handler_returns_correct_comments_count(
    mock_user_repo: Mock,
    mock_post_repo: Mock,
    mock_comment_repo: Mock,
) -> None:
    """Verify handler sets comments_count to the value from count_by_author.

    comments_count must reflect the total number of comments made by
    the user, not just the number of recent comments.
    """
    mock_comment_repo.count_by_author.return_value = 33

    query = GetUserActivityQuery(user_id=42)

    result = get_user_activity_query_handler(
        query=query,
        user_repo=mock_user_repo,
        post_repo=mock_post_repo,
        comment_repo=mock_comment_repo,
    )

    assert result.comments_count == 33
    mock_comment_repo.count_by_author.assert_called_once_with(42)


def test_handler_requests_last_5_recent_posts(
    mock_user_repo: Mock,
    mock_post_repo: Mock,
    mock_comment_repo: Mock,
) -> None:
    """Verify handler calls post_repo.find_by_author with limit=5.

    The spec requires the last 5 posts for the activity summary.
    Passing limit=5 to the repository ensures we do not over-fetch.
    """
    query = GetUserActivityQuery(user_id=42)

    get_user_activity_query_handler(
        query=query,
        user_repo=mock_user_repo,
        post_repo=mock_post_repo,
        comment_repo=mock_comment_repo,
    )

    mock_post_repo.find_by_author.assert_called_once_with(42, limit=5)


def test_handler_requests_last_10_recent_comments(
    mock_user_repo: Mock,
    mock_post_repo: Mock,
    mock_comment_repo: Mock,
) -> None:
    """Verify handler calls comment_repo.find_by_author with limit=10.

    The spec requires the last 10 comments for the activity summary.
    Passing limit=10 to the repository ensures we do not over-fetch.
    """
    query = GetUserActivityQuery(user_id=42)

    get_user_activity_query_handler(
        query=query,
        user_repo=mock_user_repo,
        post_repo=mock_post_repo,
        comment_repo=mock_comment_repo,
    )

    mock_comment_repo.find_by_author.assert_called_once_with(42, limit=10)


def test_handler_returns_zero_counts_when_no_activity(
    mock_user_repo: Mock,
) -> None:
    """Verify handler returns zero counts and empty lists for an inactive user.

    A user who has never posted or commented should produce posts_count=0,
    comments_count=0, recent_posts=[], and recent_comments=[].
    """
    post_repo = Mock()
    post_repo.find_by_author.return_value = []
    post_repo.count_by_author.return_value = 0

    comment_repo = Mock()
    comment_repo.find_by_author.return_value = []
    comment_repo.count_by_author.return_value = 0

    query = GetUserActivityQuery(user_id=42)

    result = get_user_activity_query_handler(
        query=query,
        user_repo=mock_user_repo,
        post_repo=post_repo,
        comment_repo=comment_repo,
    )

    assert result.posts_count == 0
    assert result.comments_count == 0
    assert result.recent_posts == []
    assert result.recent_comments == []


def test_handler_does_not_call_repos_when_user_not_found(
    mock_post_repo: Mock,
    mock_comment_repo: Mock,
) -> None:
    """Verify post_repo and comment_repo are never called when user is missing.

    If the user lookup fails the handler must raise immediately without
    querying the post or comment repositories, avoiding unnecessary work
    and potential confusion from stale repository state.
    """
    user_repo = Mock()
    user_repo.find_by_id.return_value = None

    query = GetUserActivityQuery(user_id=99)

    with pytest.raises(ValueError):
        get_user_activity_query_handler(
            query=query,
            user_repo=user_repo,
            post_repo=mock_post_repo,
            comment_repo=mock_comment_repo,
        )

    mock_post_repo.find_by_author.assert_not_called()
    mock_post_repo.count_by_author.assert_not_called()
    mock_comment_repo.find_by_author.assert_not_called()
    mock_comment_repo.count_by_author.assert_not_called()


def test_handler_preserves_post_aggregate_properties(
    mock_user_repo: Mock,
    mock_post_repo: Mock,
    mock_comment_repo: Mock,
    mock_post: Mock,
) -> None:
    """Verify recent_posts contains the exact Post objects from the repository.

    The handler must not wrap, copy, or transform the Post aggregates
    returned by find_by_author. Callers receive the same objects so
    no data is lost in transit.
    """
    extra_post = Mock()
    extra_post.id = 2
    extra_post.title = "Second Post"
    extra_post.author_id = 42
    extra_post.published_at = datetime(2025, 2, 1, tzinfo=UTC)

    mock_post_repo.find_by_author.return_value = [mock_post, extra_post]

    query = GetUserActivityQuery(user_id=42)

    result = get_user_activity_query_handler(
        query=query,
        user_repo=mock_user_repo,
        post_repo=mock_post_repo,
        comment_repo=mock_comment_repo,
    )

    assert len(result.recent_posts) == 2
    assert result.recent_posts[0] is mock_post
    assert result.recent_posts[1] is extra_post


def test_handler_preserves_comment_aggregate_properties(
    mock_user_repo: Mock,
    mock_post_repo: Mock,
    mock_comment_repo: Mock,
    mock_comment: Mock,
) -> None:
    """Verify recent_comments contains the exact Comment objects from the repository.

    The handler must not wrap, copy, or transform the Comment aggregates
    returned by find_by_author. Callers receive the same objects so
    no data is lost in transit.
    """
    extra_comment = Mock()
    extra_comment.id = 2
    extra_comment.post_id = 11
    extra_comment.author_id = 42
    extra_comment.created_at = datetime(2025, 2, 5, tzinfo=UTC)

    mock_comment_repo.find_by_author.return_value = [
        mock_comment,
        extra_comment,
    ]

    query = GetUserActivityQuery(user_id=42)

    result = get_user_activity_query_handler(
        query=query,
        user_repo=mock_user_repo,
        post_repo=mock_post_repo,
        comment_repo=mock_comment_repo,
    )

    assert len(result.recent_comments) == 2
    assert result.recent_comments[0] is mock_comment
    assert result.recent_comments[1] is extra_comment


def test_handler_last_login_is_none(
    mock_user_repo: Mock,
    mock_post_repo: Mock,
    mock_comment_repo: Mock,
) -> None:
    """Verify last_login is None because User aggregate has no last_login_at field.

    The User aggregate does not currently track last login time.
    The handler must return last_login=None rather than fabricating
    a value or raising an error, allowing future addition of the field
    without breaking the interface.
    """
    query = GetUserActivityQuery(user_id=42)

    result = get_user_activity_query_handler(
        query=query,
        user_repo=mock_user_repo,
        post_repo=mock_post_repo,
        comment_repo=mock_comment_repo,
    )

    assert result.last_login is None
