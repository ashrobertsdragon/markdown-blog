"""Unit tests for list_posts_query_handler.

This module defines comprehensive unit tests for the list_posts_query_handler
following TDD Red phase principles. These tests will initially fail until
the handler is implemented.

Test Coverage:
- List all posts (filter=ALL) with pagination (2 tests)
- List only drafts (filter=DRAFTS) (1 test)
- List only published posts (filter=PUBLISHED) (1 test)
- Pagination calculation (total_pages = ceil(total_count / limit)) (2 tests)
- Offset calculation ((page-1) * limit) (2 tests)
- Empty result set (author has no posts) (1 test)
- Page beyond total pages (returns empty posts list) (1 test)
- Sort order verification (most recent updated_at first) (1 test)
- Response dataclass structure (1 test)

Total: 12+ unit tests
"""

from datetime import UTC, datetime
from math import ceil
from unittest.mock import Mock

import pytest
from backend.application.queries.handlers.list_posts_query_handler import (
    ListPostsResponse,
    list_posts_query_handler,
)
from backend.application.queries.list_posts_query import (
    ListPostsQuery,
    PostFilter,
)

from backend.domain.aggregates.post import Post
from backend.domain.value_objects.slug import Slug


@pytest.fixture
def mock_post_repo() -> Mock:
    """Fixture providing mock PostRepository."""
    return Mock()


@pytest.fixture
def sample_posts_fixture() -> list[Post]:
    """Fixture providing sample Post aggregates with different timestamps.

    Creates 5 posts with timestamps from newest to oldest to verify
    sort order handling.
    """
    posts = []
    for i in range(5):
        post = Post(
            id=i + 1,
            slug=Slug(f"post-{i}"),
            title=f"Post {i}",
            author_id=42,
            _html_content=None,
            published=False,
            published_at=None,
            created_at=datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC),
            updated_at=datetime(2025, 1, i + 1, 12, 0, 0, tzinfo=UTC),
        )
        posts.append(post)

    return sorted(posts, key=lambda p: p.updated_at, reverse=True)


def test_handler_returns_list_posts_response_structure() -> None:
    """Verify handler returns ListPostsResponse with correct fields.

    This test ensures the response dataclass has all required fields:
    - posts: list of Post aggregates
    - total_count: total number of matching posts
    - total_pages: calculated total pages
    - current_page: the requested page number
    - limit: the requested page size
    """
    mock_repo = Mock()
    mock_repo.find_by_author_filtered.return_value = ([], 0)

    query = ListPostsQuery(author_id=42)

    response = list_posts_query_handler(query=query, post_repo=mock_repo)

    assert isinstance(response, ListPostsResponse)
    assert hasattr(response, "posts")
    assert hasattr(response, "total_count")
    assert hasattr(response, "total_pages")
    assert hasattr(response, "current_page")
    assert hasattr(response, "limit")
    assert isinstance(response.posts, list)
    assert isinstance(response.total_count, int)
    assert isinstance(response.total_pages, int)
    assert isinstance(response.current_page, int)
    assert isinstance(response.limit, int)


def test_handler_lists_all_posts_with_default_pagination(
    sample_posts_fixture: list[Post], mock_post_repo: Mock
) -> None:
    """Verify handler lists all posts with default pagination.

    This test ensures the handler:
    1. Calls repository with filter=ALL, limit=20, offset=0
    2. Returns all matching posts
    3. Calculates total_pages correctly
    4. Sets current_page=1
    """
    mock_post_repo.find_by_author_filtered.return_value = (
        sample_posts_fixture,
        5,
    )

    query = ListPostsQuery(author_id=42)

    response = list_posts_query_handler(query=query, post_repo=mock_post_repo)

    mock_post_repo.find_by_author_filtered.assert_called_once_with(
        author_id=42, filter_type=PostFilter.ALL, limit=20, offset=0
    )
    assert len(response.posts) == 5
    assert response.total_count == 5
    assert response.total_pages == 1
    assert response.current_page == 1
    assert response.limit == 20


def test_handler_lists_all_posts_with_custom_pagination(
    sample_posts_fixture: list[Post], mock_post_repo: Mock
) -> None:
    """Verify handler lists posts with custom page and limit.

    This test ensures the handler correctly handles custom pagination:
    - page=2, limit=10
    - offset should be calculated as (2-1) * 10 = 10
    """
    mock_post_repo.find_by_author_filtered.return_value = (
        sample_posts_fixture[:3],
        25,
    )

    query = ListPostsQuery(author_id=42, page=2, limit=10)

    response = list_posts_query_handler(query=query, post_repo=mock_post_repo)

    mock_post_repo.find_by_author_filtered.assert_called_once_with(
        author_id=42, filter_type=PostFilter.ALL, limit=10, offset=10
    )
    assert len(response.posts) == 3
    assert response.total_count == 25
    assert response.current_page == 2
    assert response.limit == 10


def test_handler_lists_only_drafts(
    sample_posts_fixture: list[Post], mock_post_repo: Mock
) -> None:
    """Verify handler filters for unpublished posts only.

    This test ensures the handler passes PostFilter.DRAFTS to repository,
    which should return only posts where published=False.
    """
    draft_posts = [p for p in sample_posts_fixture if not p.published]
    mock_post_repo.find_by_author_filtered.return_value = (draft_posts, 5)

    query = ListPostsQuery(author_id=42, filter=PostFilter.DRAFTS)

    response = list_posts_query_handler(query=query, post_repo=mock_post_repo)

    mock_post_repo.find_by_author_filtered.assert_called_once_with(
        author_id=42, filter_type=PostFilter.DRAFTS, limit=20, offset=0
    )
    assert len(response.posts) == 5
    assert all(not p.published for p in response.posts)


def test_handler_lists_only_published_posts(
    sample_posts_fixture: list[Post], mock_post_repo: Mock
) -> None:
    """Verify handler filters for published posts only.

    This test ensures the handler passes PostFilter.PUBLISHED to repository,
    which should return only posts where published=True.
    """
    for post in sample_posts_fixture[:3]:
        post.publish("<p>Test content</p>")

    published_posts = [p for p in sample_posts_fixture if p.published]
    mock_post_repo.find_by_author_filtered.return_value = (
        published_posts,
        3,
    )

    query = ListPostsQuery(author_id=42, filter=PostFilter.PUBLISHED)

    response = list_posts_query_handler(query=query, post_repo=mock_post_repo)

    mock_post_repo.find_by_author_filtered.assert_called_once_with(
        author_id=42, filter_type=PostFilter.PUBLISHED, limit=20, offset=0
    )
    assert len(response.posts) == 3
    assert all(p.published for p in response.posts)


def test_handler_calculates_total_pages_correctly(
    mock_post_repo: Mock,
) -> None:
    """Verify handler calculates total_pages = ceil(total_count / limit).

    This test ensures pagination calculation is correct:
    - 25 total posts with limit=10 should give 3 pages (ceil(25/10) = 3)
    - 20 total posts with limit=10 should give 2 pages (ceil(20/10) = 2)
    - 19 total posts with limit=20 should give 1 page (ceil(19/20) = 1)
    """
    mock_post_repo.find_by_author_filtered.return_value = ([], 25)

    query = ListPostsQuery(author_id=42, limit=10)

    response = list_posts_query_handler(query=query, post_repo=mock_post_repo)

    assert response.total_pages == ceil(25 / 10)
    assert response.total_pages == 3


def test_handler_calculates_total_pages_for_exact_division(
    mock_post_repo: Mock,
) -> None:
    """Verify handler calculates total_pages correctly when evenly divisible.

    This test ensures edge case: 20 posts / 10 limit = exactly 2 pages.
    """
    mock_post_repo.find_by_author_filtered.return_value = ([], 20)

    query = ListPostsQuery(author_id=42, limit=10)

    response = list_posts_query_handler(query=query, post_repo=mock_post_repo)

    assert response.total_pages == 2


def test_handler_calculates_offset_correctly(mock_post_repo: Mock) -> None:
    """Verify handler calculates offset = (page - 1) * limit.

    This test ensures offset calculation for different page numbers:
    - page=1: offset=0
    - page=2: offset=20 (with limit=20)
    - page=3: offset=40 (with limit=20)
    - page=5, limit=10: offset=40
    """
    mock_post_repo.find_by_author_filtered.return_value = ([], 100)

    test_cases = [
        (1, 20, 0),
        (2, 20, 20),
        (3, 20, 40),
        (5, 10, 40),
    ]

    for page, limit, expected_offset in test_cases:
        mock_post_repo.reset_mock()
        query = ListPostsQuery(author_id=42, page=page, limit=limit)

        list_posts_query_handler(query=query, post_repo=mock_post_repo)

        mock_post_repo.find_by_author_filtered.assert_called_once_with(
            author_id=42,
            filter_type=PostFilter.ALL,
            limit=limit,
            offset=expected_offset,
        )


def test_handler_returns_empty_list_when_author_has_no_posts(
    mock_post_repo: Mock,
) -> None:
    """Verify handler returns empty posts list when author has no posts.

    This test ensures edge case handling for authors with no posts:
    - posts list should be empty
    - total_count should be 0
    - total_pages should be 0
    """
    mock_post_repo.find_by_author_filtered.return_value = ([], 0)

    query = ListPostsQuery(author_id=99)

    response = list_posts_query_handler(query=query, post_repo=mock_post_repo)

    assert response.posts == []
    assert response.total_count == 0
    assert response.total_pages == 0
    assert response.current_page == 1


def test_handler_returns_empty_list_when_page_beyond_total_pages(
    mock_post_repo: Mock,
) -> None:
    """Verify handler returns empty posts list when page exceeds total_pages.

    This test ensures edge case handling when requesting a page beyond
    available data (e.g., page=10 when only 2 pages exist):
    - posts list should be empty
    - total_count should still reflect actual total
    - total_pages should be correct
    - current_page should reflect requested page
    """
    mock_post_repo.find_by_author_filtered.return_value = ([], 25)

    query = ListPostsQuery(author_id=42, page=10, limit=10)

    response = list_posts_query_handler(query=query, post_repo=mock_post_repo)

    mock_post_repo.find_by_author_filtered.assert_called_once_with(
        author_id=42, filter_type=PostFilter.ALL, limit=10, offset=90
    )
    assert response.posts == []
    assert response.total_count == 25
    assert response.total_pages == 3
    assert response.current_page == 10


def test_handler_verifies_sort_order_most_recent_first(
    sample_posts_fixture: list[Post], mock_post_repo: Mock
) -> None:
    """Verify handler returns posts sorted by updated_at DESC.

    This test ensures posts are returned in reverse chronological order
    (most recently updated first). The repository is responsible for
    sorting, but the handler should return them in that order.
    """
    mock_post_repo.find_by_author_filtered.return_value = (
        sample_posts_fixture,
        5,
    )

    query = ListPostsQuery(author_id=42)

    response = list_posts_query_handler(query=query, post_repo=mock_post_repo)

    for i in range(len(response.posts) - 1):
        assert response.posts[i].updated_at >= response.posts[i + 1].updated_at


def test_handler_preserves_post_aggregate_properties(
    sample_posts_fixture: list[Post], mock_post_repo: Mock
) -> None:
    """Verify handler returns complete Post aggregates without modification.

    This test ensures the handler doesn't modify Post objects. All
    aggregate properties (slug, title, published, etc.) should be
    preserved exactly as returned from repository.
    """
    original_post = sample_posts_fixture[0]
    mock_post_repo.find_by_author_filtered.return_value = ([original_post], 1)

    query = ListPostsQuery(author_id=42)

    response = list_posts_query_handler(query=query, post_repo=mock_post_repo)

    returned_post = response.posts[0]
    assert returned_post.id == original_post.id
    assert returned_post.slug == original_post.slug
    assert returned_post.title == original_post.title
    assert returned_post.author_id == original_post.author_id
    assert returned_post.published == original_post.published
    assert returned_post.created_at == original_post.created_at
    assert returned_post.updated_at == original_post.updated_at


def test_handler_with_single_post_calculates_one_page(
    sample_posts_fixture: list[Post], mock_post_repo: Mock
) -> None:
    """Verify handler calculates 1 page when total_count <= limit.

    This test ensures edge case: 1 post with limit=20 should give 1 page.
    """
    mock_post_repo.find_by_author_filtered.return_value = (
        sample_posts_fixture[:1],
        1,
    )

    query = ListPostsQuery(author_id=42, limit=20)

    response = list_posts_query_handler(query=query, post_repo=mock_post_repo)

    assert response.total_count == 1
    assert response.total_pages == 1
    assert len(response.posts) == 1


def test_list_posts_response_dataclass_is_frozen() -> None:
    """Verify ListPostsResponse is immutable (frozen dataclass).

    This test ensures the response dataclass cannot be modified after
    creation, preventing accidental mutation of response objects.
    """
    response = ListPostsResponse(
        posts=[], total_count=0, total_pages=0, current_page=1, limit=20
    )

    with pytest.raises((AttributeError, TypeError)):
        response.posts = []  # type: ignore[misc]

    with pytest.raises((AttributeError, TypeError)):
        response.total_count = 10  # type: ignore[misc]


def test_list_posts_response_repr_includes_metadata() -> None:
    """Verify ListPostsResponse repr includes pagination metadata.

    This test ensures the string representation shows pagination info,
    which is useful for debugging and logging.
    """
    response = ListPostsResponse(
        posts=[], total_count=100, total_pages=5, current_page=2, limit=20
    )

    repr_str = repr(response)

    assert "ListPostsResponse" in repr_str
    assert "100" in repr_str
    assert "5" in repr_str
    assert "2" in repr_str
    assert "20" in repr_str


def test_handler_with_limit_one_returns_single_post(
    sample_posts_fixture: list[Post], mock_post_repo: Mock
) -> None:
    """Verify handler works with minimum limit=1.

    This test ensures edge case: limit=1 should request only 1 post
    per page and calculate total_pages accordingly.
    """
    mock_post_repo.find_by_author_filtered.return_value = (
        sample_posts_fixture[:1],
        50,
    )

    query = ListPostsQuery(author_id=42, limit=1)

    response = list_posts_query_handler(query=query, post_repo=mock_post_repo)

    mock_post_repo.find_by_author_filtered.assert_called_once_with(
        author_id=42, filter_type=PostFilter.ALL, limit=1, offset=0
    )
    assert len(response.posts) == 1
    assert response.total_pages == 50


def test_handler_with_limit_one_hundred_maximum(
    sample_posts_fixture: list[Post], mock_post_repo: Mock
) -> None:
    """Verify handler works with maximum limit=100.

    This test ensures edge case: limit=100 should be accepted and
    used for repository query.
    """
    mock_post_repo.find_by_author_filtered.return_value = (
        sample_posts_fixture,
        100,
    )

    query = ListPostsQuery(author_id=42, limit=100)

    response = list_posts_query_handler(query=query, post_repo=mock_post_repo)

    mock_post_repo.find_by_author_filtered.assert_called_once_with(
        author_id=42, filter_type=PostFilter.ALL, limit=100, offset=0
    )
    assert response.limit == 100
    assert response.total_pages == 1
