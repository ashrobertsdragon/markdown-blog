"""Integration tests for admin API routes blueprint.

Tests the /api/admin endpoints with real Flask test client and mocked
dependencies. Verifies admin-only access, command/query execution, and error
handling for all admin operations.

These tests follow TDD principles and will FAIL until routes are implemented.
"""

from datetime import UTC, datetime
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from backend.domain.aggregates.comment import Comment
from backend.domain.aggregates.post import Post
from backend.domain.aggregates.user import User
from backend.domain.value_objects.comment_text import CommentText
from backend.domain.value_objects.role import Role
from backend.exceptions import NotFoundError


@pytest.fixture
def admin_user() -> User:
    """Return an admin user for testing."""
    return User(
        id=1,
        clerk_user_id="clerk_admin_123",
        email="admin@example.com",
        role=Role.ADMIN,
        created_at=datetime(2024, 1, 1, 12, 0, 0, tzinfo=UTC),
    )


@pytest.fixture
def regular_user() -> User:
    """Return a regular authenticated user (not admin)."""
    return User(
        id=5,
        clerk_user_id="clerk_user_456",
        email="user@example.com",
        role=Role.AUTHENTICATED,
        created_at=datetime(2024, 2, 1, 12, 0, 0, tzinfo=UTC),
    )


@pytest.fixture
def author_user() -> User:
    """Return an author user."""
    return User(
        id=10,
        clerk_user_id="clerk_author_789",
        email="author@example.com",
        role=Role.AUTHOR,
        created_at=datetime(2024, 1, 15, 12, 0, 0, tzinfo=UTC),
    )


@pytest.fixture
def admin_jwt_payload() -> dict[str, Any]:
    """Return a valid admin JWT payload."""
    return {
        "sub": "clerk_admin_123",
        "email": "admin@example.com",
        "exp": 1735689600,
    }


@pytest.fixture
def regular_jwt_payload() -> dict[str, Any]:
    """Return a valid regular user JWT payload."""
    return {
        "sub": "clerk_user_456",
        "email": "user@example.com",
        "exp": 1735689600,
    }


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
def unpublished_post() -> Post:
    """Return an unpublished (draft) post for testing."""
    post = Post.create_draft(
        slug="unpublished-draft",
        title="Unpublished Draft",
        author_id=10,
    )
    post.id = 2
    return post


@pytest.fixture
def comment(published_post: Post, regular_user: User) -> Comment:
    """Return a comment for testing."""
    assert published_post.id is not None
    assert regular_user.id is not None
    return Comment(
        id=1,
        post_id=published_post.id,
        author_id=regular_user.id,
        _text=CommentText("This is a test comment"),
        parent_id=None,
        created_at=datetime(2024, 6, 1, tzinfo=UTC),
        updated_at=datetime(2024, 6, 1, tzinfo=UTC),
        is_deleted=False,
        is_pending_moderation=False,
    )


@pytest.fixture
def user_with_posts(author_user: User) -> User:
    """Return a user with posts and comments for activity testing."""
    return author_user


# Test 1: Authorization checks


def test_unpublish_post_requires_admin_role(
    client: Any, regular_user: User, regular_jwt_payload: dict[str, Any]
) -> None:
    """Non-admin users get 403 Forbidden when trying to unpublish posts."""
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
            "/api/admin/posts/1/unpublish",
            headers={"Authorization": "Bearer user_token_123"},
        )

    assert response.status_code == 403
    assert "error" in response.json


def test_unpublish_post_requires_authentication(client: Any) -> None:
    """Unauthenticated users get 401 Unauthorized."""
    response = client.post("/api/admin/posts/1/unpublish")

    assert response.status_code == 401
    assert "error" in response.json


def test_get_user_activity_requires_admin_role(
    client: Any, regular_user: User, regular_jwt_payload: dict[str, Any]
) -> None:
    """Non-admin users get 403 Forbidden when viewing user activity."""
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
        response = client.get(
            "/api/admin/users/1/activity",
            headers={"Authorization": "Bearer user_token_123"},
        )

    assert response.status_code == 403


def test_get_system_health_requires_admin_role(
    client: Any, regular_user: User, regular_jwt_payload: dict[str, Any]
) -> None:
    """Non-admin users get 403 Forbidden when viewing system health."""
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
        response = client.get(
            "/api/admin/system/health",
            headers={"Authorization": "Bearer user_token_123"},
        )

    assert response.status_code == 403


def test_get_error_logs_requires_admin_role(
    client: Any, regular_user: User, regular_jwt_payload: dict[str, Any]
) -> None:
    """Non-admin users get 403 Forbidden when viewing error logs."""
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
        response = client.get(
            "/api/admin/system/errors",
            headers={"Authorization": "Bearer user_token_123"},
        )

    assert response.status_code == 403


# Test 2: Happy path tests


def test_unpublish_post_success(
    client: Any,
    admin_user: User,
    admin_jwt_payload: dict[str, Any],
    published_post: Post,
) -> None:
    """Admin can successfully unpublish a published post."""
    mock_clerk_adapter = MagicMock()
    mock_clerk_adapter.verify_token.return_value = admin_jwt_payload

    mock_user_repo = MagicMock()
    mock_user_repo.find_by_clerk_user_id.return_value = admin_user

    mock_handler = MagicMock()
    mock_handler.handle.return_value = published_post

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
            "backend.api.routes.admin._get_unpublish_post_handler",
            return_value=mock_handler,
        ),
    ):
        response = client.post(
            f"/api/admin/posts/{published_post.id}/unpublish",
            headers={"Authorization": "Bearer admin_token_123"},
        )

    assert response.status_code == 200
    assert "message" in response.json
    assert response.json["message"] == "Post unpublished"


def test_get_user_activity_success(
    client: Any,
    admin_user: User,
    admin_jwt_payload: dict[str, Any],
    user_with_posts: User,
) -> None:
    """Admin can successfully view user activity."""
    from backend.application.queries.get_user_activity_query import UserActivity

    mock_clerk_adapter = MagicMock()
    mock_clerk_adapter.verify_token.return_value = admin_jwt_payload

    mock_user_repo = MagicMock()
    mock_user_repo.find_by_clerk_user_id.return_value = admin_user

    activity_response = UserActivity(
        last_login=datetime(2024, 6, 1, 12, 0, 0, tzinfo=UTC),
        posts_count=5,
        comments_count=10,
        recent_posts=[],
        recent_comments=[],
    )

    mock_handler = MagicMock()
    mock_handler.handle.return_value = activity_response

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
            "backend.api.routes.admin._get_user_activity_handler",
            return_value=mock_handler,
        ),
    ):
        response = client.get(
            f"/api/admin/users/{user_with_posts.id}/activity",
            headers={"Authorization": "Bearer admin_token_123"},
        )

    assert response.status_code == 200
    assert "user_id" in response.json
    assert "posts_count" in response.json
    assert "comments_count" in response.json
    assert response.json["posts_count"] == 5


def test_get_system_health_success(
    client: Any, admin_user: User, admin_jwt_payload: dict[str, Any]
) -> None:
    """Admin can successfully view system health."""
    from backend.application.queries.get_system_health_query import SystemHealth

    mock_clerk_adapter = MagicMock()
    mock_clerk_adapter.verify_token.return_value = admin_jwt_payload

    mock_user_repo = MagicMock()
    mock_user_repo.find_by_clerk_user_id.return_value = admin_user

    health_response = SystemHealth(
        status="healthy",
        database="healthy",
        filesystem="healthy",
        github_api="healthy",
        uptime_seconds=123456,
        checked_at="2026-01-01T00:00:00+00:00",
    )

    mock_handler = MagicMock()
    mock_handler.handle.return_value = health_response

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
            "backend.api.routes.admin._get_system_health_handler",
            return_value=mock_handler,
        ),
    ):
        response = client.get(
            "/api/admin/system/health",
            headers={"Authorization": "Bearer admin_token_123"},
        )

    assert response.status_code == 200
    assert "status" in response.json
    assert "database" in response.json
    assert "filesystem" in response.json
    assert "github_api" in response.json
    assert "uptime_seconds" in response.json
    assert "checked_at" in response.json


def test_get_error_logs_success(
    client: Any, admin_user: User, admin_jwt_payload: dict[str, Any]
) -> None:
    """Admin can successfully view error logs."""
    mock_clerk_adapter = MagicMock()
    mock_clerk_adapter.verify_token.return_value = admin_jwt_payload

    mock_user_repo = MagicMock()
    mock_user_repo.find_by_clerk_user_id.return_value = admin_user

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
            "backend.api.routes.admin.ErrorLogger.get_recent_errors",
            return_value=[],
        ),
    ):
        response = client.get(
            "/api/admin/system/errors",
            headers={"Authorization": "Bearer admin_token_123"},
        )

    assert response.status_code == 200
    assert "errors" in response.json
    assert isinstance(response.json["errors"], list)


# Test 3: Error handling


def test_unpublish_post_not_found(
    client: Any, admin_user: User, admin_jwt_payload: dict[str, Any]
) -> None:
    """Unpublish non-existent post returns 404."""
    mock_clerk_adapter = MagicMock()
    mock_clerk_adapter.verify_token.return_value = admin_jwt_payload

    mock_user_repo = MagicMock()
    mock_user_repo.find_by_clerk_user_id.return_value = admin_user

    mock_handler = MagicMock()
    mock_handler.handle.side_effect = NotFoundError("Post not found")

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
            "backend.api.routes.admin._get_unpublish_post_handler",
            return_value=mock_handler,
        ),
    ):
        response = client.post(
            "/api/admin/posts/99999/unpublish",
            headers={"Authorization": "Bearer admin_token_123"},
        )

    assert response.status_code == 404
    assert "error" in response.json


def test_get_user_activity_not_found(
    client: Any, admin_user: User, admin_jwt_payload: dict[str, Any]
) -> None:
    """View non-existent user activity returns 404."""
    mock_clerk_adapter = MagicMock()
    mock_clerk_adapter.verify_token.return_value = admin_jwt_payload

    mock_user_repo = MagicMock()
    mock_user_repo.find_by_clerk_user_id.return_value = admin_user

    mock_handler = MagicMock()
    mock_handler.handle.side_effect = NotFoundError("User not found")

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
            "backend.api.routes.admin._get_user_activity_handler",
            return_value=mock_handler,
        ),
    ):
        response = client.get(
            "/api/admin/users/99999/activity",
            headers={"Authorization": "Bearer admin_token_123"},
        )

    assert response.status_code == 404
    assert "error" in response.json


# Test 4: Validation errors


def test_unpublish_already_unpublished(
    client: Any,
    admin_user: User,
    admin_jwt_payload: dict[str, Any],
    unpublished_post: Post,
) -> None:
    """Cannot unpublish already-unpublished post returns 400."""
    mock_clerk_adapter = MagicMock()
    mock_clerk_adapter.verify_token.return_value = admin_jwt_payload

    mock_user_repo = MagicMock()
    mock_user_repo.find_by_clerk_user_id.return_value = admin_user

    mock_handler = MagicMock()
    mock_handler.handle.side_effect = ValueError("Post already unpublished")

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
            "backend.api.routes.admin._get_unpublish_post_handler",
            return_value=mock_handler,
        ),
    ):
        response = client.post(
            f"/api/admin/posts/{unpublished_post.id}/unpublish",
            headers={"Authorization": "Bearer admin_token_123"},
        )

    assert response.status_code == 400
    assert "error" in response.json
    assert "already unpublished" in response.json["error"].lower()


# Test group: User list


def test_list_users_requires_admin_role(
    client: Any, regular_user: User, regular_jwt_payload: dict[str, Any]
) -> None:
    """Non-admin users get 403 when listing users."""
    mock_clerk = MagicMock()
    mock_clerk.verify_token.return_value = regular_jwt_payload
    mock_user_repo = MagicMock()
    mock_user_repo.find_by_clerk_user_id.return_value = regular_user

    with (
        patch(
            "backend.api.middleware.auth_middleware._get_clerk_adapter",
            return_value=mock_clerk,
        ),
        patch(
            "backend.api.middleware.auth_middleware._get_user_repository",
            return_value=mock_user_repo,
        ),
    ):
        response = client.get(
            "/api/admin/users",
            headers={"Authorization": "Bearer regular_token"},
        )

    assert response.status_code == 403


def test_list_users_success(
    client: Any, admin_user: User, admin_jwt_payload: dict[str, Any]
) -> None:
    """Admin receives paginated user list with required fields."""
    mock_clerk = MagicMock()
    mock_clerk.verify_token.return_value = admin_jwt_payload
    mock_auth_user_repo = MagicMock()
    mock_auth_user_repo.find_by_clerk_user_id.return_value = admin_user

    mock_admin_user_repo = MagicMock()
    mock_admin_user_repo.list_all.return_value = [admin_user]
    mock_admin_user_repo.count_all.return_value = 1

    with (
        patch(
            "backend.api.middleware.auth_middleware._get_clerk_adapter",
            return_value=mock_clerk,
        ),
        patch(
            "backend.api.middleware.auth_middleware._get_user_repository",
            return_value=mock_auth_user_repo,
        ),
        patch(
            "backend.api.routes.admin._get_user_repository",
            return_value=mock_admin_user_repo,
        ),
    ):
        response = client.get(
            "/api/admin/users",
            headers={"Authorization": "Bearer admin_token_123"},
        )

    assert response.status_code == 200
    body = response.json
    assert "users" in body
    assert "total_count" in body
    assert "total_pages" in body
    assert "page" in body
    assert "limit" in body
    assert len(body["users"]) == 1
    user_entry = body["users"][0]
    assert user_entry["email"] == "admin@example.com"
    assert user_entry["role"] == "admin"


# Test group: Update user role


def test_update_user_role_success(
    client: Any,
    admin_user: User,
    admin_jwt_payload: dict[str, Any],
    author_user: User,
) -> None:
    """Admin can promote a user to admin role."""
    mock_clerk = MagicMock()
    mock_clerk.verify_token.return_value = admin_jwt_payload
    mock_auth_user_repo = MagicMock()
    mock_auth_user_repo.find_by_clerk_user_id.return_value = admin_user

    promoted = User(
        id=author_user.id,
        clerk_user_id=author_user.clerk_user_id,
        email=author_user.email,
        role=Role.ADMIN,
        created_at=author_user.created_at,
    )
    mock_admin_user_repo = MagicMock()
    mock_admin_user_repo.find_by_id.return_value = author_user
    mock_admin_user_repo.save.return_value = promoted

    with (
        patch(
            "backend.api.middleware.auth_middleware._get_clerk_adapter",
            return_value=mock_clerk,
        ),
        patch(
            "backend.api.middleware.auth_middleware._get_user_repository",
            return_value=mock_auth_user_repo,
        ),
        patch(
            "backend.api.routes.admin._get_user_repository",
            return_value=mock_admin_user_repo,
        ),
    ):
        response = client.put(
            f"/api/admin/users/{author_user.id}/role",
            json={"role": "admin"},
            headers={"Authorization": "Bearer admin_token_123"},
        )

    assert response.status_code == 200
    assert response.json["role"] == "admin"


def test_update_user_role_invalid_role_returns_422(
    client: Any, admin_user: User, admin_jwt_payload: dict[str, Any]
) -> None:
    """Invalid role value returns 422 Unprocessable Entity."""
    mock_clerk = MagicMock()
    mock_clerk.verify_token.return_value = admin_jwt_payload
    mock_user_repo = MagicMock()
    mock_user_repo.find_by_clerk_user_id.return_value = admin_user

    with (
        patch(
            "backend.api.middleware.auth_middleware._get_clerk_adapter",
            return_value=mock_clerk,
        ),
        patch(
            "backend.api.middleware.auth_middleware._get_user_repository",
            return_value=mock_user_repo,
        ),
    ):
        response = client.put(
            "/api/admin/users/1/role",
            json={"role": "superuser"},
            headers={"Authorization": "Bearer admin_token_123"},
        )

    assert response.status_code == 422


def test_update_user_role_not_found_returns_404(
    client: Any, admin_user: User, admin_jwt_payload: dict[str, Any]
) -> None:
    """Unknown user ID returns 404."""
    mock_clerk = MagicMock()
    mock_clerk.verify_token.return_value = admin_jwt_payload
    mock_auth_user_repo = MagicMock()
    mock_auth_user_repo.find_by_clerk_user_id.return_value = admin_user

    mock_admin_user_repo = MagicMock()
    mock_admin_user_repo.find_by_id.return_value = None

    with (
        patch(
            "backend.api.middleware.auth_middleware._get_clerk_adapter",
            return_value=mock_clerk,
        ),
        patch(
            "backend.api.middleware.auth_middleware._get_user_repository",
            return_value=mock_auth_user_repo,
        ),
        patch(
            "backend.api.routes.admin._get_user_repository",
            return_value=mock_admin_user_repo,
        ),
    ):
        response = client.put(
            "/api/admin/users/9999/role",
            json={"role": "admin"},
            headers={"Authorization": "Bearer admin_token_123"},
        )

    assert response.status_code == 404


# Test group: Post list


def test_list_posts_requires_admin_role(
    client: Any, regular_user: User, regular_jwt_payload: dict[str, Any]
) -> None:
    """Non-admin users get 403 when listing posts via admin endpoint."""
    mock_clerk = MagicMock()
    mock_clerk.verify_token.return_value = regular_jwt_payload
    mock_user_repo = MagicMock()
    mock_user_repo.find_by_clerk_user_id.return_value = regular_user

    with (
        patch(
            "backend.api.middleware.auth_middleware._get_clerk_adapter",
            return_value=mock_clerk,
        ),
        patch(
            "backend.api.middleware.auth_middleware._get_user_repository",
            return_value=mock_user_repo,
        ),
    ):
        response = client.get(
            "/api/admin/posts",
            headers={"Authorization": "Bearer regular_token"},
        )

    assert response.status_code == 403


def test_list_posts_success(
    client: Any,
    admin_user: User,
    admin_jwt_payload: dict[str, Any],
    published_post: Post,
) -> None:
    """Admin receives paginated published post list with required fields."""
    mock_clerk = MagicMock()
    mock_clerk.verify_token.return_value = admin_jwt_payload
    mock_auth_user_repo = MagicMock()
    mock_auth_user_repo.find_by_clerk_user_id.return_value = admin_user

    published_post.id = 1
    mock_post_repo = MagicMock()
    mock_post_repo.list_published.return_value = [published_post]
    mock_post_repo.count_published.return_value = 1

    mock_admin_user_repo = MagicMock()
    mock_admin_user_repo.find_by_id.return_value = admin_user

    with (
        patch(
            "backend.api.middleware.auth_middleware._get_clerk_adapter",
            return_value=mock_clerk,
        ),
        patch(
            "backend.api.middleware.auth_middleware._get_user_repository",
            return_value=mock_auth_user_repo,
        ),
        patch(
            "backend.api.routes.admin._get_post_repository",
            return_value=mock_post_repo,
        ),
        patch(
            "backend.api.routes.admin._get_user_repository",
            return_value=mock_admin_user_repo,
        ),
    ):
        response = client.get(
            "/api/admin/posts",
            headers={"Authorization": "Bearer admin_token_123"},
        )

    assert response.status_code == 200
    body = response.json
    assert "posts" in body
    assert "total_count" in body
    assert len(body["posts"]) == 1
    post_entry = body["posts"][0]
    assert post_entry["slug"] == "published-article"
    assert "author" in post_entry
    assert "published_at" in post_entry


# Test group: Comment list


def test_list_comments_requires_admin_role(
    client: Any, regular_user: User, regular_jwt_payload: dict[str, Any]
) -> None:
    """Non-admin users get 403 when listing comments via admin endpoint."""
    mock_clerk = MagicMock()
    mock_clerk.verify_token.return_value = regular_jwt_payload
    mock_user_repo = MagicMock()
    mock_user_repo.find_by_clerk_user_id.return_value = regular_user

    with (
        patch(
            "backend.api.middleware.auth_middleware._get_clerk_adapter",
            return_value=mock_clerk,
        ),
        patch(
            "backend.api.middleware.auth_middleware._get_user_repository",
            return_value=mock_user_repo,
        ),
    ):
        response = client.get(
            "/api/admin/comments",
            headers={"Authorization": "Bearer regular_token"},
        )

    assert response.status_code == 403


def test_list_comments_success(
    client: Any,
    admin_user: User,
    admin_jwt_payload: dict[str, Any],
    comment: Comment,
    published_post: Post,
) -> None:
    """Admin receives paginated comment list with required fields."""
    mock_clerk = MagicMock()
    mock_clerk.verify_token.return_value = admin_jwt_payload
    mock_auth_user_repo = MagicMock()
    mock_auth_user_repo.find_by_clerk_user_id.return_value = admin_user

    mock_comment_repo = MagicMock()
    mock_comment_repo.list_all_admin.return_value = [comment]
    mock_comment_repo.count_all_admin.return_value = 1

    mock_admin_user_repo = MagicMock()
    mock_admin_user_repo.find_by_id.return_value = User(
        id=comment.author_id,
        clerk_user_id="c",
        email="commenter@example.com",
        role=Role.AUTHENTICATED,
        created_at=datetime(2024, 1, 1, tzinfo=UTC),
    )

    published_post.id = comment.post_id
    mock_post_repo = MagicMock()
    mock_post_repo.find_by_id.return_value = published_post

    with (
        patch(
            "backend.api.middleware.auth_middleware._get_clerk_adapter",
            return_value=mock_clerk,
        ),
        patch(
            "backend.api.middleware.auth_middleware._get_user_repository",
            return_value=mock_auth_user_repo,
        ),
        patch(
            "backend.api.routes.admin._get_comment_repository",
            return_value=mock_comment_repo,
        ),
        patch(
            "backend.api.routes.admin._get_user_repository",
            return_value=mock_admin_user_repo,
        ),
        patch(
            "backend.api.routes.admin._get_post_repository",
            return_value=mock_post_repo,
        ),
    ):
        response = client.get(
            "/api/admin/comments",
            headers={"Authorization": "Bearer admin_token_123"},
        )

    assert response.status_code == 200
    body = response.json
    assert "comments" in body
    assert "total_count" in body
    assert len(body["comments"]) == 1
    comment_entry = body["comments"][0]
    assert "text" in comment_entry
    assert "author" in comment_entry
    assert "post_title" in comment_entry
