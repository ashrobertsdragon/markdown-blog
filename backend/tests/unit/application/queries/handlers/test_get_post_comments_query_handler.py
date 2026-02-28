"""Unit tests for handle_get_post_comments.

Tests public vs admin comment retrieval, pagination has_more logic,
and total_count calculation. Repository is mocked.
"""

from unittest.mock import Mock

import backend.application.queries.handlers.get_post_comments_query_handler as _h  # noqa: E501
from backend.application.queries.get_post_comments_query import (
    GetPostCommentsQuery,
    GetPostCommentsResponse,
)
from backend.domain.aggregates.comment import Comment
from backend.infrastructure.persistence.comment_repository import (
    CommentRepository,
)

handle_get_post_comments = _h.handle_get_post_comments


def _comment(n: int) -> Comment:
    c = Comment.create(post_id=1, author_id=1, text=f"Comment {n}")
    c.id = n
    return c


def _repo(comments: list[Comment]) -> Mock:
    repo = Mock(spec=CommentRepository)
    repo.list_by_post.return_value = comments
    repo.list_by_post_admin.return_value = comments
    return repo


def test_returns_response_type() -> None:
    """Handler returns a GetPostCommentsResponse."""
    repo = _repo([])
    query = GetPostCommentsQuery(post_id=1)

    result = handle_get_post_comments(query, repo)

    assert isinstance(result, GetPostCommentsResponse)


def test_public_view_calls_list_by_post() -> None:
    """show_pending=False calls list_by_post, not list_by_post_admin."""
    repo = _repo([])
    query = GetPostCommentsQuery(post_id=1, show_pending=False)

    handle_get_post_comments(query, repo)

    repo.list_by_post.assert_called_once()
    repo.list_by_post_admin.assert_not_called()


def test_admin_view_calls_list_by_post_admin() -> None:
    """show_pending=True calls list_by_post_admin, not list_by_post."""
    repo = _repo([])
    query = GetPostCommentsQuery(post_id=1, show_pending=True)

    handle_get_post_comments(query, repo)

    repo.list_by_post_admin.assert_called_once()
    repo.list_by_post.assert_not_called()


def test_has_more_false_when_results_under_limit() -> None:
    """has_more is False when fewer items than limit are returned."""
    comments = [_comment(i) for i in range(3)]
    repo = _repo(comments)
    query = GetPostCommentsQuery(post_id=1, limit=5)

    result = handle_get_post_comments(query, repo)

    assert result.has_more is False
    assert len(result.comments) == 3


def test_has_more_true_when_extra_item_returned() -> None:
    """has_more is True when repository returns limit+1 items."""
    comments = [_comment(i) for i in range(6)]
    repo = _repo(comments)
    query = GetPostCommentsQuery(post_id=1, limit=5)

    result = handle_get_post_comments(query, repo)

    assert result.has_more is True
    assert len(result.comments) == 5


def test_total_count_exact_when_no_more() -> None:
    """total_count equals skip + page size when has_more is False."""
    comments = [_comment(i) for i in range(3)]
    repo = _repo(comments)
    query = GetPostCommentsQuery(post_id=1, skip=10, limit=5)

    result = handle_get_post_comments(query, repo)

    assert result.total_count == 13


def test_total_count_lower_bound_when_has_more() -> None:
    """total_count is at least skip + limit + 1 when has_more is True."""
    comments = [_comment(i) for i in range(6)]
    repo = _repo(comments)
    query = GetPostCommentsQuery(post_id=1, skip=0, limit=5)

    result = handle_get_post_comments(query, repo)

    assert result.total_count == 6
    assert result.has_more is True


def test_empty_post_returns_empty_response() -> None:
    """A post with no comments returns an empty response."""
    repo = _repo([])
    query = GetPostCommentsQuery(post_id=1)

    result = handle_get_post_comments(query, repo)

    assert result.comments == []
    assert result.total_count == 0
    assert result.has_more is False


def test_repository_receives_correct_post_id_and_pagination() -> None:
    """Repository is called with the correct post_id, skip, and limit+1."""
    repo = _repo([])
    query = GetPostCommentsQuery(post_id=7, skip=20, limit=10)

    handle_get_post_comments(query, repo)

    repo.list_by_post.assert_called_once_with(7, skip=20, limit=11)
