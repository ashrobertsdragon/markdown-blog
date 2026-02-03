"""Integration tests for posts API routes blueprint.

Tests the /posts blueprint endpoints with real Flask test client and mocked
dependencies (filesystem, GitHub, database). These tests verify the full HTTP
request/response flow including auth, validation, and error handling for all
8 post management endpoints.

These tests follow TDD principles and will FAIL until routes are implemented.
"""

from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

import pytest

from backend.application.queries.list_posts_query import ListPostsResponse
from backend.domain.aggregates.post import Post
from backend.domain.aggregates.user import User
from backend.domain.value_objects.role import Role


@pytest.fixture
def author_user() -> User:
    """Return an author user for testing post creation."""
    return User(
        id=10,
        clerk_user_id="clerk_author_123",
        email="author@example.com",
        role=Role.AUTHOR,
        created_at=datetime(2024, 1, 1, 12, 0, 0, tzinfo=UTC),
    )


@pytest.fixture
def admin_user() -> User:
    """Return an admin user for testing admin capabilities."""
    return User(
        id=20,
        clerk_user_id="clerk_admin_456",
        email="admin@example.com",
        role=Role.ADMIN,
        created_at=datetime(2024, 1, 1, 12, 0, 0, tzinfo=UTC),
    )


@pytest.fixture
def regular_user() -> User:
    """Return a regular authenticated user (not author or admin)."""
    return User(
        id=30,
        clerk_user_id="clerk_user_789",
        email="user@example.com",
        role=Role.AUTHENTICATED,
        created_at=datetime(2024, 1, 1, 12, 0, 0, tzinfo=UTC),
    )


@pytest.fixture
def author_jwt_payload() -> dict[str, object]:
    """Return a valid author JWT payload."""
    return {
        "sub": "clerk_author_123",
        "email": "author@example.com",
        "exp": 1735689600,
    }


@pytest.fixture
def admin_jwt_payload() -> dict[str, object]:
    """Return a valid admin JWT payload."""
    return {
        "sub": "clerk_admin_456",
        "email": "admin@example.com",
        "exp": 1735689600,
    }


@pytest.fixture
def regular_jwt_payload() -> dict[str, object]:
    """Return a valid regular user JWT payload."""
    return {
        "sub": "clerk_user_789",
        "email": "user@example.com",
        "exp": 1735689600,
    }


@pytest.fixture
def draft_post() -> Post:
    """Return a draft post for testing."""
    return Post.create_draft(
        slug="my-first-post",
        title="My First Post",
        author_id=10,
    )


@pytest.fixture
def published_post() -> Post:
    """Return a published post for testing."""
    post = Post.create_draft(
        slug="published-article",
        title="Published Article",
        author_id=10,
    )
    post.publish("<p>Test content</p>")
    post.id = 1
    return post


@pytest.fixture
def other_author_post() -> Post:
    """Return a post by a different author."""
    return Post.create_draft(
        slug="other-author-post",
        title="Other Author Post",
        author_id=99,
    )


def test_create_draft_with_valid_data_returns_201(
    client, author_user, author_jwt_payload
):
    """POST /api/posts with valid slug and title should return 201.

    Tests successful draft creation flow:
    1. Author sends POST with slug and title
    2. Handler creates draft via CreateDraftCommand
    3. Draft saved to filesystem and committed to GitHub
    4. Returns 201 with draft metadata
    """
    mock_clerk_adapter = MagicMock()
    mock_clerk_adapter.verify_token.return_value = author_jwt_payload

    mock_user_repo = MagicMock()
    mock_user_repo.find_by_clerk_user_id.return_value = author_user

    mock_handler = MagicMock()
    draft = Post.create_draft(slug="new-post", title="New Post", author_id=10)
    draft.id = 42
    mock_handler.handle.return_value = draft

    with (
        patch(
            "backend.api.middleware.auth_middleware._get_clerk_adapter",
            return_value=mock_clerk_adapter,
        ),
        patch(
            "backend.api.middleware.auth_middleware._get_user_repository",
            return_value=mock_user_repo,
        ),
        patch(
            "backend.api.routes.posts._get_create_draft_handler",
            return_value=mock_handler,
        ),
    ):
        response = client.post(
            "/api/posts",
            headers={"Authorization": "Bearer author_token"},
            json={"slug": "new-post", "title": "New Post"},
        )

    assert response.status_code == 201
    assert response.json["slug"] == "new-post"
    assert response.json["title"] == "New Post"
    assert response.json["published"] is False
    assert "created_at" in response.json


def test_create_draft_without_auth_returns_401(client):
    """POST /api/posts without Authorization header should return 401."""
    response = client.post(
        "/api/posts",
        json={"slug": "new-post", "title": "New Post"},
    )

    assert response.status_code == 401
    assert "error" in response.json


def test_create_draft_without_author_role_returns_403(
    client, regular_user, regular_jwt_payload
):
    """POST /api/posts with non-author user should return 403.

    Only AUTHOR and ADMIN roles should be able to create drafts.
    """
    mock_clerk_adapter = MagicMock()
    mock_clerk_adapter.verify_token.return_value = regular_jwt_payload

    mock_user_repo = MagicMock()
    mock_user_repo.find_by_clerk_user_id.return_value = regular_user

    with (
        patch(
            "backend.api.middleware.auth_middleware._get_clerk_adapter",
            return_value=mock_clerk_adapter,
        ),
        patch(
            "backend.api.middleware.auth_middleware._get_user_repository",
            return_value=mock_user_repo,
        ),
    ):
        response = client.post(
            "/api/posts",
            headers={"Authorization": "Bearer user_token"},
            json={"slug": "new-post", "title": "New Post"},
        )

    assert response.status_code == 403


def test_create_draft_with_invalid_slug_returns_400(
    client, author_user, author_jwt_payload
):
    """POST /api/posts with invalid slug should return 400.

    Slug must be lowercase, alphanumeric with hyphens only.
    """
    mock_clerk_adapter = MagicMock()
    mock_clerk_adapter.verify_token.return_value = author_jwt_payload

    mock_user_repo = MagicMock()
    mock_user_repo.find_by_clerk_user_id.return_value = author_user

    with (
        patch(
            "backend.api.middleware.auth_middleware._get_clerk_adapter",
            return_value=mock_clerk_adapter,
        ),
        patch(
            "backend.api.middleware.auth_middleware._get_user_repository",
            return_value=mock_user_repo,
        ),
    ):
        response = client.post(
            "/api/posts",
            headers={"Authorization": "Bearer author_token"},
            json={"slug": "Invalid_Slug!", "title": "Test"},
        )

    assert response.status_code == 400
    assert "slug" in response.json["error"].lower()


def test_create_draft_with_duplicate_slug_returns_400(
    client, author_user, author_jwt_payload
):
    """POST /api/posts with duplicate slug should return 400.

    Slugs must be unique across all posts.
    """
    mock_clerk_adapter = MagicMock()
    mock_clerk_adapter.verify_token.return_value = author_jwt_payload

    mock_user_repo = MagicMock()
    mock_user_repo.find_by_clerk_user_id.return_value = author_user

    mock_handler = MagicMock()
    mock_handler.handle.side_effect = ValueError("Slug already exists")

    with (
        patch(
            "backend.api.middleware.auth_middleware._get_clerk_adapter",
            return_value=mock_clerk_adapter,
        ),
        patch(
            "backend.api.middleware.auth_middleware._get_user_repository",
            return_value=mock_user_repo,
        ),
        patch(
            "backend.api.routes.posts._get_create_draft_handler",
            return_value=mock_handler,
        ),
    ):
        response = client.post(
            "/api/posts",
            headers={"Authorization": "Bearer author_token"},
            json={"slug": "existing-post", "title": "Test"},
        )

    assert response.status_code == 400
    assert "slug" in response.json["error"].lower()


def test_create_draft_with_missing_title_returns_400(
    client, author_user, author_jwt_payload
):
    """POST /api/posts without title field should return 400."""
    mock_clerk_adapter = MagicMock()
    mock_clerk_adapter.verify_token.return_value = author_jwt_payload

    mock_user_repo = MagicMock()
    mock_user_repo.find_by_clerk_user_id.return_value = author_user

    with (
        patch(
            "backend.api.middleware.auth_middleware._get_clerk_adapter",
            return_value=mock_clerk_adapter,
        ),
        patch(
            "backend.api.middleware.auth_middleware._get_user_repository",
            return_value=mock_user_repo,
        ),
    ):
        response = client.post(
            "/api/posts",
            headers={"Authorization": "Bearer author_token"},
            json={"slug": "test-post"},
        )

    assert response.status_code == 400
    assert "title" in response.json["error"].lower()


def test_create_draft_with_missing_slug_returns_400(
    client, author_user, author_jwt_payload
):
    """POST /api/posts without slug field should return 400."""
    mock_clerk_adapter = MagicMock()
    mock_clerk_adapter.verify_token.return_value = author_jwt_payload

    mock_user_repo = MagicMock()
    mock_user_repo.find_by_clerk_user_id.return_value = author_user

    with (
        patch(
            "backend.api.middleware.auth_middleware._get_clerk_adapter",
            return_value=mock_clerk_adapter,
        ),
        patch(
            "backend.api.middleware.auth_middleware._get_user_repository",
            return_value=mock_user_repo,
        ),
    ):
        response = client.post(
            "/api/posts",
            headers={"Authorization": "Bearer author_token"},
            json={"title": "Test Post"},
        )

    assert response.status_code == 400
    assert "slug" in response.json["error"].lower()


def test_get_draft_by_slug_returns_200(
    client, author_user, author_jwt_payload, draft_post
):
    """GET /api/posts/:slug should return 200 with draft content.

    Tests retrieving draft from filesystem for viewing/editing.
    """
    mock_clerk_adapter = MagicMock()
    mock_clerk_adapter.verify_token.return_value = author_jwt_payload

    mock_user_repo = MagicMock()
    mock_user_repo.find_by_clerk_user_id.return_value = author_user

    mock_query_handler = MagicMock()
    mock_query_handler.handle.return_value = draft_post

    with (
        patch(
            "backend.api.middleware.auth_middleware._get_clerk_adapter",
            return_value=mock_clerk_adapter,
        ),
        patch(
            "backend.api.middleware.auth_middleware._get_user_repository",
            return_value=mock_user_repo,
        ),
        patch(
            "backend.api.routes.posts._get_get_post_query_handler",
            return_value=mock_query_handler,
        ),
    ):
        response = client.get(
            "/api/posts/my-first-post",
            headers={"Authorization": "Bearer author_token"},
        )

    assert response.status_code == 200
    assert response.json["slug"] == "my-first-post"
    assert response.json["title"] == "My First Post"


def test_get_draft_by_nonexistent_slug_returns_404(
    client, author_user, author_jwt_payload
):
    """GET /api/posts/:slug for non-existent draft should return 404."""
    mock_clerk_adapter = MagicMock()
    mock_clerk_adapter.verify_token.return_value = author_jwt_payload

    mock_user_repo = MagicMock()
    mock_user_repo.find_by_clerk_user_id.return_value = author_user

    mock_query_handler = MagicMock()
    mock_query_handler.handle.return_value = None

    with (
        patch(
            "backend.api.middleware.auth_middleware._get_clerk_adapter",
            return_value=mock_clerk_adapter,
        ),
        patch(
            "backend.api.middleware.auth_middleware._get_user_repository",
            return_value=mock_user_repo,
        ),
        patch(
            "backend.api.routes.posts._get_get_post_query_handler",
            return_value=mock_query_handler,
        ),
    ):
        response = client.get(
            "/api/posts/nonexistent",
            headers={"Authorization": "Bearer author_token"},
        )

    assert response.status_code == 404


def test_get_draft_by_other_author_returns_403(
    client, author_user, author_jwt_payload, other_author_post
):
    """GET /api/posts/:slug for another author's draft should return 403.

    Authors can only access their own drafts unless they're admin.
    """
    mock_clerk_adapter = MagicMock()
    mock_clerk_adapter.verify_token.return_value = author_jwt_payload

    mock_user_repo = MagicMock()
    mock_user_repo.find_by_clerk_user_id.return_value = author_user

    mock_query_handler = MagicMock()
    mock_query_handler.handle.return_value = other_author_post

    with (
        patch(
            "backend.api.middleware.auth_middleware._get_clerk_adapter",
            return_value=mock_clerk_adapter,
        ),
        patch(
            "backend.api.middleware.auth_middleware._get_user_repository",
            return_value=mock_user_repo,
        ),
        patch(
            "backend.api.routes.posts._get_get_post_query_handler",
            return_value=mock_query_handler,
        ),
    ):
        response = client.get(
            "/api/posts/other-author-post",
            headers={"Authorization": "Bearer author_token"},
        )

    assert response.status_code == 403


def test_get_draft_without_auth_returns_401(client):
    """GET /api/posts/:slug without Authorization should return 401."""
    response = client.get("/api/posts/my-first-post")

    assert response.status_code == 401


def test_save_draft_with_valid_content_returns_200(
    client, author_user, author_jwt_payload, draft_post
):
    """PUT /api/posts/:slug with content should return 200.

    Tests updating draft content in filesystem and committing to GitHub.
    """
    mock_clerk_adapter = MagicMock()
    mock_clerk_adapter.verify_token.return_value = author_jwt_payload

    mock_user_repo = MagicMock()
    mock_user_repo.find_by_clerk_user_id.return_value = author_user

    mock_handler = MagicMock()
    mock_handler.handle.return_value = draft_post

    with (
        patch(
            "backend.api.middleware.auth_middleware._get_clerk_adapter",
            return_value=mock_clerk_adapter,
        ),
        patch(
            "backend.api.middleware.auth_middleware._get_user_repository",
            return_value=mock_user_repo,
        ),
        patch(
            "backend.api.routes.posts._get_save_draft_handler",
            return_value=mock_handler,
        ),
    ):
        response = client.put(
            "/api/posts/my-first-post",
            headers={"Authorization": "Bearer author_token"},
            json={"content": "# Updated content\n\nNew paragraph"},
        )

    assert response.status_code == 200
    mock_handler.handle.assert_called_once()


def test_save_draft_without_content_field_returns_400(
    client, author_user, author_jwt_payload
):
    """PUT /api/posts/:slug without content field should return 400."""
    mock_clerk_adapter = MagicMock()
    mock_clerk_adapter.verify_token.return_value = author_jwt_payload

    mock_user_repo = MagicMock()
    mock_user_repo.find_by_clerk_user_id.return_value = author_user

    with (
        patch(
            "backend.api.middleware.auth_middleware._get_clerk_adapter",
            return_value=mock_clerk_adapter,
        ),
        patch(
            "backend.api.middleware.auth_middleware._get_user_repository",
            return_value=mock_user_repo,
        ),
    ):
        response = client.put(
            "/api/posts/my-first-post",
            headers={"Authorization": "Bearer author_token"},
            json={},
        )

    assert response.status_code == 400
    assert "content" in response.json["error"].lower()


def test_save_draft_for_nonexistent_post_returns_404(
    client, author_user, author_jwt_payload
):
    """PUT /api/posts/:slug for non-existent post should return 404."""
    mock_clerk_adapter = MagicMock()
    mock_clerk_adapter.verify_token.return_value = author_jwt_payload

    mock_user_repo = MagicMock()
    mock_user_repo.find_by_clerk_user_id.return_value = author_user

    mock_handler = MagicMock()
    mock_handler.handle.side_effect = ValueError("Post not found")

    with (
        patch(
            "backend.api.middleware.auth_middleware._get_clerk_adapter",
            return_value=mock_clerk_adapter,
        ),
        patch(
            "backend.api.middleware.auth_middleware._get_user_repository",
            return_value=mock_user_repo,
        ),
        patch(
            "backend.api.routes.posts._get_save_draft_handler",
            return_value=mock_handler,
        ),
    ):
        response = client.put(
            "/api/posts/nonexistent",
            headers={"Authorization": "Bearer author_token"},
            json={"content": "Test"},
        )

    assert response.status_code == 404


def test_save_draft_for_other_author_returns_403(
    client, author_user, author_jwt_payload
):
    """PUT /api/posts/:slug for another author's draft should return 403."""
    mock_clerk_adapter = MagicMock()
    mock_clerk_adapter.verify_token.return_value = author_jwt_payload

    mock_user_repo = MagicMock()
    mock_user_repo.find_by_clerk_user_id.return_value = author_user

    mock_handler = MagicMock()
    mock_handler.handle.side_effect = ValueError(
        "Cannot edit another author's post"
    )

    with (
        patch(
            "backend.api.middleware.auth_middleware._get_clerk_adapter",
            return_value=mock_clerk_adapter,
        ),
        patch(
            "backend.api.middleware.auth_middleware._get_user_repository",
            return_value=mock_user_repo,
        ),
        patch(
            "backend.api.routes.posts._get_save_draft_handler",
            return_value=mock_handler,
        ),
    ):
        response = client.put(
            "/api/posts/other-author-post",
            headers={"Authorization": "Bearer author_token"},
            json={"content": "Test"},
        )

    assert response.status_code == 403


def test_save_draft_without_auth_returns_401(client):
    """PUT /api/posts/:slug without Authorization should return 401."""
    response = client.put(
        "/api/posts/my-first-post",
        json={"content": "Test"},
    )

    assert response.status_code == 401


def test_delete_draft_returns_204(
    client, author_user, author_jwt_payload, draft_post
):
    """DELETE /api/posts/:slug should return 204 on success.

    Tests deleting draft from filesystem and database.
    """
    mock_clerk_adapter = MagicMock()
    mock_clerk_adapter.verify_token.return_value = author_jwt_payload

    mock_user_repo = MagicMock()
    mock_user_repo.find_by_clerk_user_id.return_value = author_user

    mock_handler = MagicMock()
    mock_handler.handle.return_value = None

    with (
        patch(
            "backend.api.middleware.auth_middleware._get_clerk_adapter",
            return_value=mock_clerk_adapter,
        ),
        patch(
            "backend.api.middleware.auth_middleware._get_user_repository",
            return_value=mock_user_repo,
        ),
        patch(
            "backend.api.routes.posts._get_delete_draft_handler",
            return_value=mock_handler,
        ),
    ):
        response = client.delete(
            "/api/posts/my-first-post",
            headers={"Authorization": "Bearer author_token"},
        )

    assert response.status_code == 204
    assert response.data == b""


def test_delete_published_post_returns_400(
    client, author_user, author_jwt_payload
):
    """DELETE /api/posts/:slug for published post should return 400.

    Published posts cannot be deleted, only unpublished.
    """
    mock_clerk_adapter = MagicMock()
    mock_clerk_adapter.verify_token.return_value = author_jwt_payload

    mock_user_repo = MagicMock()
    mock_user_repo.find_by_clerk_user_id.return_value = author_user

    mock_handler = MagicMock()
    mock_handler.handle.side_effect = ValueError("Cannot delete published post")

    with (
        patch(
            "backend.api.middleware.auth_middleware._get_clerk_adapter",
            return_value=mock_clerk_adapter,
        ),
        patch(
            "backend.api.middleware.auth_middleware._get_user_repository",
            return_value=mock_user_repo,
        ),
        patch(
            "backend.api.routes.posts._get_delete_draft_handler",
            return_value=mock_handler,
        ),
    ):
        response = client.delete(
            "/api/posts/published-article",
            headers={"Authorization": "Bearer author_token"},
        )

    assert response.status_code == 400
    assert "published" in response.json["error"].lower()


def test_delete_nonexistent_draft_returns_404(
    client, author_user, author_jwt_payload
):
    """DELETE /api/posts/:slug for non-existent draft should return 404."""
    mock_clerk_adapter = MagicMock()
    mock_clerk_adapter.verify_token.return_value = author_jwt_payload

    mock_user_repo = MagicMock()
    mock_user_repo.find_by_clerk_user_id.return_value = author_user

    mock_handler = MagicMock()
    mock_handler.handle.side_effect = ValueError("Post not found")

    with (
        patch(
            "backend.api.middleware.auth_middleware._get_clerk_adapter",
            return_value=mock_clerk_adapter,
        ),
        patch(
            "backend.api.middleware.auth_middleware._get_user_repository",
            return_value=mock_user_repo,
        ),
        patch(
            "backend.api.routes.posts._get_delete_draft_handler",
            return_value=mock_handler,
        ),
    ):
        response = client.delete(
            "/api/posts/nonexistent",
            headers={"Authorization": "Bearer author_token"},
        )

    assert response.status_code == 404


def test_delete_draft_without_auth_returns_401(client):
    """DELETE /api/posts/:slug without Authorization should return 401."""
    response = client.delete("/api/posts/my-first-post")

    assert response.status_code == 401


def test_publish_post_converts_markdown_to_html_returns_200(
    client, author_user, author_jwt_payload, draft_post
):
    """POST /api/posts/:slug/publish should return 200 with published post.

    Tests publishing flow:
    1. Read markdown from filesystem
    2. Convert to sanitized HTML
    3. Save to database with published=true
    4. Update front matter in markdown file
    """
    mock_clerk_adapter = MagicMock()
    mock_clerk_adapter.verify_token.return_value = author_jwt_payload

    mock_user_repo = MagicMock()
    mock_user_repo.find_by_clerk_user_id.return_value = author_user

    mock_handler = MagicMock()
    published = Post.create_draft(
        slug="my-first-post", title="My First Post", author_id=10
    )
    published.publish("<p>Test content</p>")
    mock_handler.handle.return_value = published

    with (
        patch(
            "backend.api.middleware.auth_middleware._get_clerk_adapter",
            return_value=mock_clerk_adapter,
        ),
        patch(
            "backend.api.middleware.auth_middleware._get_user_repository",
            return_value=mock_user_repo,
        ),
        patch(
            "backend.api.routes.posts._get_publish_post_handler",
            return_value=mock_handler,
        ),
    ):
        response = client.post(
            "/api/posts/my-first-post/publish",
            headers={"Authorization": "Bearer author_token"},
        )

    assert response.status_code == 200
    assert response.json["published"] is True
    assert "published_at" in response.json


def test_publish_already_published_post_returns_400(
    client, author_user, author_jwt_payload
):
    """POST /api/posts/:slug/publish for already published post returns 400."""
    mock_clerk_adapter = MagicMock()
    mock_clerk_adapter.verify_token.return_value = author_jwt_payload

    mock_user_repo = MagicMock()
    mock_user_repo.find_by_clerk_user_id.return_value = author_user

    mock_handler = MagicMock()
    mock_handler.handle.side_effect = ValueError("Post already published")

    with (
        patch(
            "backend.api.middleware.auth_middleware._get_clerk_adapter",
            return_value=mock_clerk_adapter,
        ),
        patch(
            "backend.api.middleware.auth_middleware._get_user_repository",
            return_value=mock_user_repo,
        ),
        patch(
            "backend.api.routes.posts._get_publish_post_handler",
            return_value=mock_handler,
        ),
    ):
        response = client.post(
            "/api/posts/published-article/publish",
            headers={"Authorization": "Bearer author_token"},
        )

    assert response.status_code == 400
    assert "already published" in response.json["error"].lower()


def test_publish_nonexistent_post_returns_404(
    client, author_user, author_jwt_payload
):
    """POST /api/posts/:slug/publish for non-existent post returns 404."""
    mock_clerk_adapter = MagicMock()
    mock_clerk_adapter.verify_token.return_value = author_jwt_payload

    mock_user_repo = MagicMock()
    mock_user_repo.find_by_clerk_user_id.return_value = author_user

    mock_handler = MagicMock()
    mock_handler.handle.side_effect = ValueError("Post not found")

    with (
        patch(
            "backend.api.middleware.auth_middleware._get_clerk_adapter",
            return_value=mock_clerk_adapter,
        ),
        patch(
            "backend.api.middleware.auth_middleware._get_user_repository",
            return_value=mock_user_repo,
        ),
        patch(
            "backend.api.routes.posts._get_publish_post_handler",
            return_value=mock_handler,
        ),
    ):
        response = client.post(
            "/api/posts/nonexistent/publish",
            headers={"Authorization": "Bearer author_token"},
        )

    assert response.status_code == 404


def test_publish_post_without_auth_returns_401(client):
    """POST /api/posts/:slug/publish without Authorization returns 401."""
    response = client.post("/api/posts/my-first-post/publish")

    assert response.status_code == 401


def test_unpublish_post_returns_200(
    client, author_user, author_jwt_payload, published_post
):
    """POST /api/posts/:slug/unpublish should return 200.

    Tests unpublishing flow:
    1. Set published=false in database
    2. Update front matter in markdown file
    3. Post remains in database but hidden from public
    """
    mock_clerk_adapter = MagicMock()
    mock_clerk_adapter.verify_token.return_value = author_jwt_payload

    mock_user_repo = MagicMock()
    mock_user_repo.find_by_clerk_user_id.return_value = author_user

    mock_handler = MagicMock()
    unpublished = Post.create_draft(
        slug="published-article", title="Published Article", author_id=10
    )
    unpublished.id = 1
    mock_handler.handle.return_value = unpublished

    with (
        patch(
            "backend.api.middleware.auth_middleware._get_clerk_adapter",
            return_value=mock_clerk_adapter,
        ),
        patch(
            "backend.api.middleware.auth_middleware._get_user_repository",
            return_value=mock_user_repo,
        ),
        patch(
            "backend.api.routes.posts._get_unpublish_post_handler",
            return_value=mock_handler,
        ),
    ):
        response = client.post(
            "/api/posts/published-article/unpublish",
            headers={"Authorization": "Bearer author_token"},
        )

    assert response.status_code == 200
    assert response.json["published"] is False


def test_unpublish_post_as_admin_succeeds(
    client, admin_user, admin_jwt_payload
):
    """POST /api/posts/:slug/unpublish as admin should succeed.

    Admins can unpublish any post regardless of author.
    """
    mock_clerk_adapter = MagicMock()
    mock_clerk_adapter.verify_token.return_value = admin_jwt_payload

    mock_user_repo = MagicMock()
    mock_user_repo.find_by_clerk_user_id.return_value = admin_user

    mock_handler = MagicMock()
    unpublished = Post.create_draft(
        slug="other-post", title="Other Post", author_id=99
    )
    mock_handler.handle.return_value = unpublished

    with (
        patch(
            "backend.api.middleware.auth_middleware._get_clerk_adapter",
            return_value=mock_clerk_adapter,
        ),
        patch(
            "backend.api.middleware.auth_middleware._get_user_repository",
            return_value=mock_user_repo,
        ),
        patch(
            "backend.api.routes.posts._get_unpublish_post_handler",
            return_value=mock_handler,
        ),
    ):
        response = client.post(
            "/api/posts/other-post/unpublish",
            headers={"Authorization": "Bearer admin_token"},
        )

    assert response.status_code == 200


def test_unpublish_other_author_post_as_author_returns_403(
    client, author_user, author_jwt_payload
):
    """POST /api/posts/:slug/unpublish for other author returns 403.

    Non-admin authors cannot unpublish other authors' posts.
    """
    mock_clerk_adapter = MagicMock()
    mock_clerk_adapter.verify_token.return_value = author_jwt_payload

    mock_user_repo = MagicMock()
    mock_user_repo.find_by_clerk_user_id.return_value = author_user

    mock_handler = MagicMock()
    mock_handler.handle.side_effect = ValueError(
        "Cannot unpublish another author's post"
    )

    with (
        patch(
            "backend.api.middleware.auth_middleware._get_clerk_adapter",
            return_value=mock_clerk_adapter,
        ),
        patch(
            "backend.api.middleware.auth_middleware._get_user_repository",
            return_value=mock_user_repo,
        ),
        patch(
            "backend.api.routes.posts._get_unpublish_post_handler",
            return_value=mock_handler,
        ),
    ):
        response = client.post(
            "/api/posts/other-author-post/unpublish",
            headers={"Authorization": "Bearer author_token"},
        )

    assert response.status_code == 403


def test_unpublish_post_without_auth_returns_401(client):
    """POST /api/posts/:slug/unpublish without Authorization returns 401."""
    response = client.post("/api/posts/published-article/unpublish")

    assert response.status_code == 401


def test_list_my_posts_returns_200_with_posts(
    client, author_user, author_jwt_payload
):
    """GET /api/my-posts should return 200 with author's posts.

    Tests listing posts for authenticated author with pagination.
    """
    mock_clerk_adapter = MagicMock()
    mock_clerk_adapter.verify_token.return_value = author_jwt_payload

    mock_user_repo = MagicMock()
    mock_user_repo.find_by_clerk_user_id.return_value = author_user

    mock_query_handler = MagicMock()
    draft = Post.create_draft(slug="draft-1", title="Draft 1", author_id=10)
    published = Post.create_draft(
        slug="published-1", title="Published 1", author_id=10
    )
    published.publish("<p>Content</p>")
    mock_query_handler.handle.return_value = ListPostsResponse(
        posts=[draft, published],
        total_count=2,
        total_pages=1,
        current_page=1,
        limit=20,
    )

    with (
        patch(
            "backend.api.middleware.auth_middleware._get_clerk_adapter",
            return_value=mock_clerk_adapter,
        ),
        patch(
            "backend.api.middleware.auth_middleware._get_user_repository",
            return_value=mock_user_repo,
        ),
        patch(
            "backend.api.routes.posts._get_list_posts_query_handler",
            return_value=mock_query_handler,
        ),
    ):
        response = client.get(
            "/api/my-posts",
            headers={"Authorization": "Bearer author_token"},
        )

    assert response.status_code == 200
    assert "posts" in response.json
    assert isinstance(response.json["posts"], list)
    assert len(response.json["posts"]) == 2


def test_list_my_posts_with_drafts_filter_returns_only_drafts(
    client, author_user, author_jwt_payload
):
    """GET /api/my-posts?filter=drafts should return only drafts."""
    mock_clerk_adapter = MagicMock()
    mock_clerk_adapter.verify_token.return_value = author_jwt_payload

    mock_user_repo = MagicMock()
    mock_user_repo.find_by_clerk_user_id.return_value = author_user

    mock_query_handler = MagicMock()
    draft = Post.create_draft(slug="draft-1", title="Draft 1", author_id=10)
    mock_query_handler.handle.return_value = ListPostsResponse(
        posts=[draft],
        total_count=1,
        total_pages=1,
        current_page=1,
        limit=20,
    )

    with (
        patch(
            "backend.api.middleware.auth_middleware._get_clerk_adapter",
            return_value=mock_clerk_adapter,
        ),
        patch(
            "backend.api.middleware.auth_middleware._get_user_repository",
            return_value=mock_user_repo,
        ),
        patch(
            "backend.api.routes.posts._get_list_posts_query_handler",
            return_value=mock_query_handler,
        ),
    ):
        response = client.get(
            "/api/my-posts?filter=drafts",
            headers={"Authorization": "Bearer author_token"},
        )

    assert response.status_code == 200
    assert len(response.json["posts"]) == 1
    assert response.json["posts"][0]["published"] is False


def test_list_my_posts_with_published_filter_returns_only_published(
    client, author_user, author_jwt_payload
):
    """GET /api/my-posts?filter=published should return only published posts."""
    mock_clerk_adapter = MagicMock()
    mock_clerk_adapter.verify_token.return_value = author_jwt_payload

    mock_user_repo = MagicMock()
    mock_user_repo.find_by_clerk_user_id.return_value = author_user

    mock_query_handler = MagicMock()
    published = Post.create_draft(
        slug="published-1", title="Published 1", author_id=10
    )
    published.publish("<p>Content</p>")
    mock_query_handler.handle.return_value = ListPostsResponse(
        posts=[published],
        total_count=1,
        total_pages=1,
        current_page=1,
        limit=20,
    )

    with (
        patch(
            "backend.api.middleware.auth_middleware._get_clerk_adapter",
            return_value=mock_clerk_adapter,
        ),
        patch(
            "backend.api.middleware.auth_middleware._get_user_repository",
            return_value=mock_user_repo,
        ),
        patch(
            "backend.api.routes.posts._get_list_posts_query_handler",
            return_value=mock_query_handler,
        ),
    ):
        response = client.get(
            "/api/my-posts?filter=published",
            headers={"Authorization": "Bearer author_token"},
        )

    assert response.status_code == 200
    assert len(response.json["posts"]) == 1
    assert response.json["posts"][0]["published"] is True


def test_list_my_posts_with_pagination_parameters(
    client, author_user, author_jwt_payload
):
    """GET /api/my-posts with page and limit should paginate results."""
    mock_clerk_adapter = MagicMock()
    mock_clerk_adapter.verify_token.return_value = author_jwt_payload

    mock_user_repo = MagicMock()
    mock_user_repo.find_by_clerk_user_id.return_value = author_user

    mock_query_handler = MagicMock()
    mock_query_handler.handle.return_value = ListPostsResponse(
        posts=[],
        total_count=0,
        total_pages=0,
        current_page=2,
        limit=10,
    )

    with (
        patch(
            "backend.api.middleware.auth_middleware._get_clerk_adapter",
            return_value=mock_clerk_adapter,
        ),
        patch(
            "backend.api.middleware.auth_middleware._get_user_repository",
            return_value=mock_user_repo,
        ),
        patch(
            "backend.api.routes.posts._get_list_posts_query_handler",
            return_value=mock_query_handler,
        ),
    ):
        response = client.get(
            "/api/my-posts?page=2&limit=10",
            headers={"Authorization": "Bearer author_token"},
        )

    assert response.status_code == 200
    assert "page" in response.json
    assert "limit" in response.json


def test_list_my_posts_without_auth_returns_401(client):
    """GET /api/my-posts without Authorization should return 401."""
    response = client.get("/api/my-posts")

    assert response.status_code == 401


def test_list_my_posts_returns_empty_list_for_new_author(
    client, author_user, author_jwt_payload
):
    """GET /api/my-posts should return empty list for author with no posts."""
    mock_clerk_adapter = MagicMock()
    mock_clerk_adapter.verify_token.return_value = author_jwt_payload

    mock_user_repo = MagicMock()
    mock_user_repo.find_by_clerk_user_id.return_value = author_user

    mock_query_handler = MagicMock()
    mock_query_handler.handle.return_value = ListPostsResponse(
        posts=[],
        total_count=0,
        total_pages=0,
        current_page=1,
        limit=20,
    )

    with (
        patch(
            "backend.api.middleware.auth_middleware._get_clerk_adapter",
            return_value=mock_clerk_adapter,
        ),
        patch(
            "backend.api.middleware.auth_middleware._get_user_repository",
            return_value=mock_user_repo,
        ),
        patch(
            "backend.api.routes.posts._get_list_posts_query_handler",
            return_value=mock_query_handler,
        ),
    ):
        response = client.get(
            "/api/my-posts",
            headers={"Authorization": "Bearer author_token"},
        )

    assert response.status_code == 200
    assert response.json["posts"] == []


def test_create_draft_returns_json_content_type(
    client, author_user, author_jwt_payload
):
    """POST /api/posts should return application/json content type."""
    mock_clerk_adapter = MagicMock()
    mock_clerk_adapter.verify_token.return_value = author_jwt_payload

    mock_user_repo = MagicMock()
    mock_user_repo.find_by_clerk_user_id.return_value = author_user

    mock_handler = MagicMock()
    draft = Post.create_draft(slug="new-post", title="New Post", author_id=10)
    mock_handler.handle.return_value = draft

    with (
        patch(
            "backend.api.middleware.auth_middleware._get_clerk_adapter",
            return_value=mock_clerk_adapter,
        ),
        patch(
            "backend.api.middleware.auth_middleware._get_user_repository",
            return_value=mock_user_repo,
        ),
        patch(
            "backend.api.routes.posts._get_create_draft_handler",
            return_value=mock_handler,
        ),
    ):
        response = client.post(
            "/api/posts",
            headers={"Authorization": "Bearer author_token"},
            json={"slug": "new-post", "title": "New Post"},
        )

    assert response.content_type == "application/json"


def test_admin_can_edit_any_post(client, admin_user, admin_jwt_payload):
    """Admin should be able to save drafts for any author's post."""
    mock_clerk_adapter = MagicMock()
    mock_clerk_adapter.verify_token.return_value = admin_jwt_payload

    mock_user_repo = MagicMock()
    mock_user_repo.find_by_clerk_user_id.return_value = admin_user

    mock_handler = MagicMock()
    post = Post.create_draft(
        slug="other-author", title="Other Author", author_id=99
    )
    mock_handler.handle.return_value = post

    with (
        patch(
            "backend.api.middleware.auth_middleware._get_clerk_adapter",
            return_value=mock_clerk_adapter,
        ),
        patch(
            "backend.api.middleware.auth_middleware._get_user_repository",
            return_value=mock_user_repo,
        ),
        patch(
            "backend.api.routes.posts._get_save_draft_handler",
            return_value=mock_handler,
        ),
    ):
        response = client.put(
            "/api/posts/other-author",
            headers={"Authorization": "Bearer admin_token"},
            json={"content": "Admin edit"},
        )

    assert response.status_code == 200
