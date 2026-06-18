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
