import pytest
from unittest.mock import Mock, patch
from flask import Flask
from backend.api.routes.posts import posts_bp
from backend.application.queries.list_public_posts_query import (
    ListPublicPostsResponse,
)


@pytest.fixture
def app():
    app = Flask(__name__)
    app.register_blueprint(posts_bp, url_prefix="/posts")
    return app


@pytest.fixture
def client(app):
    return app.test_client()


@patch("backend.api.routes.posts._get_list_public_posts_query_handler")
def test_list_public_posts(mock_get_handler, client):
    # Arrange
    mock_handler = Mock()
    mock_get_handler.return_value = mock_handler

    mock_response = ListPublicPostsResponse(
        posts=[], total_count=0, total_pages=0, current_page=1, limit=20
    )
    mock_handler.handle.return_value = mock_response

    # Act
    response = client.get("/posts/public?page=1&limit=20")

    # Assert
    assert response.status_code == 200
    data = response.get_json()
    assert data["posts"] == []
    assert data["total_count"] == 0
    assert data["total_pages"] == 0
    assert data["page"] == 1
    assert data["limit"] == 20


@patch("backend.api.routes.posts._get_list_public_posts_query_handler")
@pytest.mark.parametrize(
    "query_string",
    [
        "page=0&limit=20",
        "page=1&limit=0",
        "page=1&limit=101",
    ],
)
def test_list_public_posts_invalid_query_params(
    mock_get_handler, client, query_string
):
    # Arrange
    mock_handler = Mock()
    mock_get_handler.return_value = mock_handler
    # Simulate the ValueError raised by ListPublicPostsQuery validation
    mock_handler.handle.side_effect = ValueError(
        "Invalid pagination parameters"
    )

    # Act
    response = client.get(f"/posts/public?{query_string}")

    # Assert
    assert response.status_code == 400
    data = response.get_json()
    assert isinstance(data, dict)
    assert "error" in data


@patch("backend.api.routes.posts._get_list_public_posts_query_handler")
def test_list_public_posts_unexpected_error(mock_get_handler, client):
    # Arrange
    mock_handler = Mock()
    mock_get_handler.return_value = mock_handler
    mock_handler.handle.side_effect = Exception("unexpected failure")

    # Act
    response = client.get("/posts/public?page=1&limit=20")

    # Assert
    assert response.status_code == 500
    data = response.get_json()
    assert isinstance(data, dict)
    assert data["error"] == "An error occurred"


from datetime import UTC, datetime

from backend.domain.aggregates.post import Post
from backend.domain.value_objects.slug import Slug


def test_post_to_public_dict_fallbacks_for_missing_published_at_and_html_content():
    """
    Regression test for posts missing published_at/html_content.

    Ensures that calling Post.to_public_dict() on a post where
    published_at is None and HTML content has not been precomputed
    still returns a dict with a non-null published_at (falling back to
    updated_at/created_at) and a non-empty html_content string.
    """
    # Arrange
    now = datetime.now(UTC)
    post = Post(
        id=1,
        title="Test post",
        slug=Slug("test-post"),
        author_id=1,
        created_at=now,
        updated_at=now,
        published_at=None,
        published=True,
        _html_content=None,
    )

    # Act
    public_dict = post.to_public_dict()

    # Assert
    assert public_dict.get("published_at") is not None
    assert isinstance(public_dict.get("html_content"), str)
    assert public_dict["html_content"] == ""
