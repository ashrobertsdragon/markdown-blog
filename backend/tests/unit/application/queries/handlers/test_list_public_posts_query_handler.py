from unittest.mock import Mock
from backend.application.queries.list_public_posts_query import (
    ListPublicPostsQuery,
)
from backend.application.queries.handlers.list_public_posts_query_handler import (
    list_public_posts_query_handler,
)
from backend.infrastructure.persistence.post_repository import PostRepository


def test_list_public_posts_query_handler():
    # Arrange
    mock_repo = Mock(spec=PostRepository)
    mock_repo.list_published.return_value = []
    mock_repo.count_published.return_value = 0
    query = ListPublicPostsQuery(page=1, limit=10)

    # Act
    response = list_public_posts_query_handler(query, mock_repo)

    # Assert
    assert response.posts == []
    assert response.total_count == 0
    assert response.total_pages == 0
    assert response.current_page == 1
    assert response.limit == 10
    mock_repo.list_published.assert_called_once_with(limit=10, offset=0)
    mock_repo.count_published.assert_called_once()


def test_list_public_posts_query_handler_with_pagination_and_results():
    # Arrange
    mock_repo = Mock(spec=PostRepository)
    posts = ["post-1", "post-2"]
    mock_repo.list_published.return_value = posts
    mock_repo.count_published.return_value = 21
    query = ListPublicPostsQuery(page=2, limit=10)

    # Act
    response = list_public_posts_query_handler(query, mock_repo)

    # Assert
    assert response.posts == posts
    assert response.total_count == 21
    assert response.total_pages == 3
    assert response.current_page == 2
    assert response.limit == 10
    mock_repo.list_published.assert_called_once_with(limit=10, offset=10)
    mock_repo.count_published.assert_called_once()
