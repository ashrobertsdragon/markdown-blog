"""Integration tests for the comments API endpoints.

Covers the full HTTP contract for comment submission, replies, listing,
deletion, and admin moderation. Uses Flask test client with mocked
infrastructure dependencies to avoid database and external service calls.
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
from backend.domain.value_objects.slug import Slug
from backend.exceptions import AuthorizationError, RateLimitExceededError


@pytest.fixture
def valid_jwt_payload() -> dict[str, Any]:
    """Return a valid JWT payload matching Clerk's token structure."""
    return {
        "sub": "clerk_user_123",
        "email": "reader@example.com",
        "iss": "https://clerk.example.com",
        "aud": "https://api.example.com",
        "exp": 9999999999,
        "iat": 1735686000,
    }


@pytest.fixture
def admin_jwt_payload() -> dict[str, Any]:
    """Return a valid JWT payload for an admin user."""
    return {
        "sub": "clerk_admin_456",
        "email": "admin@example.com",
        "iss": "https://clerk.example.com",
        "aud": "https://api.example.com",
        "exp": 9999999999,
        "iat": 1735686000,
    }


@pytest.fixture
def reader_user() -> User:
    """Return an authenticated reader User."""
    return User(
        id=10,
        clerk_user_id="clerk_user_123",
        email="reader@example.com",
        role=Role.AUTHENTICATED,
        created_at=datetime(2024, 1, 1, tzinfo=UTC),
    )


@pytest.fixture
def admin_user() -> User:
    """Return an admin User."""
    return User(
        id=20,
        clerk_user_id="clerk_admin_456",
        email="admin@example.com",
        role=Role.ADMIN,
        created_at=datetime(2024, 1, 1, tzinfo=UTC),
    )


@pytest.fixture
def published_post() -> Post:
    """Return a published Post aggregate."""
    return Post(
        id=1,
        slug=Slug("test-post"),
        title="Test Post",
        author_id=99,
        _html_content=None,
        published=True,
        published_at=datetime(2024, 1, 1, tzinfo=UTC),
        created_at=datetime(2024, 1, 1, tzinfo=UTC),
        updated_at=datetime(2024, 1, 1, tzinfo=UTC),
    )


@pytest.fixture
def sample_comment(published_post: Post, reader_user: User) -> Comment:
    """Return a persisted Comment aggregate."""
    assert published_post.id is not None
    assert reader_user.id is not None
    return Comment(
        id=100,
        post_id=published_post.id,
        author_id=reader_user.id,
        _text=CommentText("Great post!"),
        parent_id=None,
        created_at=datetime(2024, 6, 1, tzinfo=UTC),
        updated_at=datetime(2024, 6, 1, tzinfo=UTC),
        is_deleted=False,
        is_pending_moderation=False,
    )


def _make_auth_patches(
    jwt_payload: dict[str, Any], user: User
) -> tuple[Any, Any]:
    """Return context managers that mock Clerk auth and user repository."""
    mock_clerk = MagicMock()
    mock_clerk.verify_token.return_value = jwt_payload
    mock_user_repo = MagicMock()
    mock_user_repo.find_by_clerk_user_id.return_value = user
    return (
        patch(
            "backend.api.middleware.auth_middleware._get_clerk_adapter",
            return_value=mock_clerk,
        ),
        patch(
            "backend.api.middleware.auth_middleware._get_user_repository",
            return_value=mock_user_repo,
        ),
    )


def test_post_comment_returns_201_created(
    client: Any,
    valid_jwt_payload: dict[str, Any],
    reader_user: User,
    published_post: Post,
    sample_comment: Comment,
) -> None:
    """POST /api/posts/{slug}/comments returns 201 with comment data."""
    mock_post_repo = MagicMock()
    mock_post_repo.find_by_slug.return_value = published_post

    mock_comment_repo = MagicMock()
    mock_comment_repo.save.return_value = sample_comment

    clerk_patch, user_patch = _make_auth_patches(valid_jwt_payload, reader_user)

    with (
        clerk_patch,
        user_patch,
        patch(
            "backend.api.routes.comments._get_post_repository",
            return_value=mock_post_repo,
        ),
        patch(
            "backend.api.routes.comments._get_comment_repository",
            return_value=mock_comment_repo,
        ),
        patch(
            "backend.api.routes.comments._get_rate_limit_service",
            return_value=MagicMock(),
        ),
        patch(
            "backend.api.routes.comments._get_spam_check_service",
            return_value=MagicMock(),
        ),
        patch(
            "backend.api.routes.comments.handle_post_comment",
            return_value=sample_comment,
        ),
    ):
        response = client.post(
            "/api/posts/test-post/comments",
            json={"text": "Great post!"},
            headers={"Authorization": "Bearer fake_token"},
        )

    assert response.status_code == 201
    data = response.get_json()
    assert data["id"] == sample_comment.id
    assert data["post_id"] == sample_comment.post_id


def test_rate_limit_returns_429_with_headers(
    client: Any,
    valid_jwt_payload: dict[str, Any],
    reader_user: User,
    published_post: Post,
) -> None:
    """Rate limit exceeded returns 429 with X-RateLimit-Remaining header."""
    mock_post_repo = MagicMock()
    mock_post_repo.find_by_slug.return_value = published_post

    clerk_patch, user_patch = _make_auth_patches(valid_jwt_payload, reader_user)

    with (
        clerk_patch,
        user_patch,
        patch(
            "backend.api.routes.comments._get_post_repository",
            return_value=mock_post_repo,
        ),
        patch(
            "backend.api.routes.comments._get_comment_repository",
            return_value=MagicMock(),
        ),
        patch(
            "backend.api.routes.comments._get_rate_limit_service",
            return_value=MagicMock(),
        ),
        patch(
            "backend.api.routes.comments._get_spam_check_service",
            return_value=MagicMock(),
        ),
        patch(
            "backend.api.routes.comments.handle_post_comment",
            side_effect=RateLimitExceededError(
                "Too many comments. Please wait 45 seconds.",
                reset_after=45,
                remaining=0,
            ),
        ),
    ):
        response = client.post(
            "/api/posts/test-post/comments",
            json={"text": "Hello"},
            headers={"Authorization": "Bearer fake_token"},
        )

    assert response.status_code == 429
    assert "X-RateLimit-Remaining" in response.headers
    data = response.get_json()
    assert "error" in data


def test_post_comment_unauthenticated_returns_401(client: Any) -> None:
    """POST without authentication credentials returns 401."""
    response = client.post(
        "/api/posts/test-post/comments",
        json={"text": "Hello"},
    )
    assert response.status_code == 401


def test_post_comment_empty_text_returns_400(
    client: Any,
    valid_jwt_payload: dict[str, Any],
    reader_user: User,
    published_post: Post,
) -> None:
    """POST with empty text body returns 400 with a validation error."""
    mock_post_repo = MagicMock()
    mock_post_repo.find_by_slug.return_value = published_post

    clerk_patch, user_patch = _make_auth_patches(valid_jwt_payload, reader_user)

    with (
        clerk_patch,
        user_patch,
        patch(
            "backend.api.routes.comments._get_post_repository",
            return_value=mock_post_repo,
        ),
    ):
        response = client.post(
            "/api/posts/test-post/comments",
            json={"text": ""},
            headers={"Authorization": "Bearer fake_token"},
        )

    assert response.status_code == 400
    data = response.get_json()
    assert "error" in data


def test_post_comment_unknown_slug_returns_404(
    client: Any,
    valid_jwt_payload: dict[str, Any],
    reader_user: User,
) -> None:
    """POST to a slug that does not exist returns 404."""
    mock_post_repo = MagicMock()
    mock_post_repo.find_by_slug.return_value = None

    clerk_patch, user_patch = _make_auth_patches(valid_jwt_payload, reader_user)

    with (
        clerk_patch,
        user_patch,
        patch(
            "backend.api.routes.comments._get_post_repository",
            return_value=mock_post_repo,
        ),
    ):
        response = client.post(
            "/api/posts/no-such-post/comments",
            json={"text": "Hello"},
            headers={"Authorization": "Bearer fake_token"},
        )

    assert response.status_code == 404


def test_spam_comment_returns_201_pending_moderation(
    client: Any,
    valid_jwt_payload: dict[str, Any],
    reader_user: User,
    published_post: Post,
) -> None:
    """POST with high-spam text returns 201 with is_pending_moderation=true."""
    assert published_post.id is not None
    assert reader_user.id is not None
    spam_comment = Comment(
        id=101,
        post_id=published_post.id,
        author_id=reader_user.id,
        _text=CommentText("Buy cheap pills now!!!"),
        parent_id=None,
        created_at=datetime(2024, 6, 1, tzinfo=UTC),
        updated_at=datetime(2024, 6, 1, tzinfo=UTC),
        is_deleted=False,
        is_pending_moderation=True,
    )

    mock_post_repo = MagicMock()
    mock_post_repo.find_by_slug.return_value = published_post

    mock_comment_repo = MagicMock()
    mock_comment_repo.save.return_value = spam_comment

    clerk_patch, user_patch = _make_auth_patches(valid_jwt_payload, reader_user)

    with (
        clerk_patch,
        user_patch,
        patch(
            "backend.api.routes.comments._get_post_repository",
            return_value=mock_post_repo,
        ),
        patch(
            "backend.api.routes.comments._get_comment_repository",
            return_value=mock_comment_repo,
        ),
        patch(
            "backend.api.routes.comments._get_rate_limit_service",
            return_value=MagicMock(),
        ),
        patch(
            "backend.api.routes.comments._get_spam_check_service",
            return_value=MagicMock(),
        ),
        patch(
            "backend.api.routes.comments.handle_post_comment",
            return_value=spam_comment,
        ),
    ):
        response = client.post(
            "/api/posts/test-post/comments",
            json={"text": "Buy cheap pills now!!!"},
            headers={"Authorization": "Bearer fake_token"},
        )

    assert response.status_code == 201
    data = response.get_json()
    assert data["is_pending_moderation"] is True


def test_list_comments_returns_200_with_array(
    client: Any,
    published_post: Post,
    sample_comment: Comment,
) -> None:
    """GET /api/posts/{slug}/comments returns 200 with a list of comments."""
    from backend.application.queries.get_post_comments_query import (
        GetPostCommentsResponse,
    )

    mock_post_repo = MagicMock()
    mock_post_repo.find_by_slug.return_value = published_post

    mock_response = GetPostCommentsResponse(
        comments=[sample_comment],
        total_count=1,
        has_more=False,
    )

    with (
        patch(
            "backend.api.routes.comments._get_post_repository",
            return_value=mock_post_repo,
        ),
        patch(
            "backend.api.routes.comments._get_comment_repository",
            return_value=MagicMock(),
        ),
        patch(
            "backend.api.routes.comments.handle_get_post_comments",
            return_value=mock_response,
        ),
    ):
        response = client.get("/api/posts/test-post/comments")

    assert response.status_code == 200
    data = response.get_json()
    assert "comments" in data
    assert "total_count" in data
    assert "has_more" in data
    assert len(data["comments"]) == 1


def test_list_comments_includes_is_post_author_flag(
    client: Any,
    published_post: Post,
    reader_user: User,
) -> None:
    """GET /api/posts/{slug}/comments includes is_post_author on each comment.

    Comments by the post author should have is_post_author=True; comments
    by other users should have is_post_author=False.
    """
    from backend.application.queries.get_post_comments_query import (
        GetPostCommentsResponse,
    )

    assert published_post.id is not None
    assert published_post.author_id is not None
    assert reader_user.id is not None

    comment_by_reader = Comment(
        id=100,
        post_id=published_post.id,
        author_id=reader_user.id,
        _text=CommentText("Great post!"),
        parent_id=None,
        created_at=datetime(2024, 6, 1, tzinfo=UTC),
        updated_at=datetime(2024, 6, 1, tzinfo=UTC),
        is_deleted=False,
        is_pending_moderation=False,
    )
    comment_by_author = Comment(
        id=101,
        post_id=published_post.id,
        author_id=published_post.author_id,
        _text=CommentText("Thanks everyone!"),
        parent_id=None,
        created_at=datetime(2024, 6, 1, tzinfo=UTC),
        updated_at=datetime(2024, 6, 1, tzinfo=UTC),
        is_deleted=False,
        is_pending_moderation=False,
    )

    mock_post_repo = MagicMock()
    mock_post_repo.find_by_slug.return_value = published_post

    mock_response = GetPostCommentsResponse(
        comments=[comment_by_reader, comment_by_author],
        total_count=2,
        has_more=False,
    )

    with (
        patch(
            "backend.api.routes.comments._get_post_repository",
            return_value=mock_post_repo,
        ),
        patch(
            "backend.api.routes.comments._get_comment_repository",
            return_value=MagicMock(),
        ),
        patch(
            "backend.api.routes.comments.handle_get_post_comments",
            return_value=mock_response,
        ),
    ):
        response = client.get("/api/posts/test-post/comments")

    assert response.status_code == 200
    data = response.get_json()
    comments = data["comments"]
    assert comments[0]["is_post_author"] is False
    assert comments[1]["is_post_author"] is True


def test_post_comment_includes_is_post_author_flag(
    client: Any,
    valid_jwt_payload: dict[str, Any],
    published_post: Post,
) -> None:
    """POST /api/posts/{slug}/comments includes is_post_author in the response.

    When the commenter is also the post author, is_post_author must be True.
    """
    assert published_post.id is not None
    assert published_post.author_id is not None

    author_user = User(
        id=published_post.author_id,
        clerk_user_id="clerk_user_123",
        email="author@example.com",
        role=Role.AUTHOR,
        created_at=datetime(2024, 1, 1, tzinfo=UTC),
    )
    author_comment = Comment(
        id=200,
        post_id=published_post.id,
        author_id=published_post.author_id,
        _text=CommentText("My own post!"),
        parent_id=None,
        created_at=datetime(2024, 6, 1, tzinfo=UTC),
        updated_at=datetime(2024, 6, 1, tzinfo=UTC),
        is_deleted=False,
        is_pending_moderation=False,
    )

    mock_post_repo = MagicMock()
    mock_post_repo.find_by_slug.return_value = published_post

    clerk_patch, user_patch = _make_auth_patches(valid_jwt_payload, author_user)

    with (
        clerk_patch,
        user_patch,
        patch(
            "backend.api.routes.comments._get_post_repository",
            return_value=mock_post_repo,
        ),
        patch(
            "backend.api.routes.comments._get_comment_repository",
            return_value=MagicMock(),
        ),
        patch(
            "backend.api.routes.comments._get_rate_limit_service",
            return_value=MagicMock(),
        ),
        patch(
            "backend.api.routes.comments._get_spam_check_service",
            return_value=MagicMock(),
        ),
        patch(
            "backend.api.routes.comments.handle_post_comment",
            return_value=author_comment,
        ),
    ):
        response = client.post(
            "/api/posts/test-post/comments",
            json={"text": "My own post!"},
            headers={"Authorization": "Bearer fake_token"},
        )

    assert response.status_code == 201
    data = response.get_json()
    assert data["is_post_author"] is True


def test_list_comments_unknown_slug_returns_404(client: Any) -> None:
    """GET for a slug that does not exist returns 404."""
    mock_post_repo = MagicMock()
    mock_post_repo.find_by_slug.return_value = None

    with patch(
        "backend.api.routes.comments._get_post_repository",
        return_value=mock_post_repo,
    ):
        response = client.get("/api/posts/no-such-post/comments")

    assert response.status_code == 404


def test_post_reply_returns_201_with_parent_id(
    client: Any,
    valid_jwt_payload: dict[str, Any],
    reader_user: User,
    published_post: Post,
    sample_comment: Comment,
) -> None:
    """POST /api/posts/{slug}/comments/{id}/reply returns 201 with parent_id."""
    assert published_post.id is not None
    assert reader_user.id is not None
    reply = Comment(
        id=200,
        post_id=published_post.id,
        author_id=reader_user.id,
        _text=CommentText("@Reader thanks for sharing!"),
        parent_id=sample_comment.id,
        created_at=datetime(2024, 6, 1, tzinfo=UTC),
        updated_at=datetime(2024, 6, 1, tzinfo=UTC),
        is_deleted=False,
        is_pending_moderation=False,
    )

    mock_post_repo = MagicMock()
    mock_post_repo.find_by_slug.return_value = published_post

    mock_comment_repo = MagicMock()
    mock_comment_repo.save.return_value = reply

    clerk_patch, user_patch = _make_auth_patches(valid_jwt_payload, reader_user)

    with (
        clerk_patch,
        user_patch,
        patch(
            "backend.api.routes.comments._get_post_repository",
            return_value=mock_post_repo,
        ),
        patch(
            "backend.api.routes.comments._get_comment_repository",
            return_value=mock_comment_repo,
        ),
        patch(
            "backend.api.routes.comments._get_rate_limit_service",
            return_value=MagicMock(),
        ),
        patch(
            "backend.api.routes.comments._get_spam_check_service",
            return_value=MagicMock(),
        ),
        patch(
            "backend.api.routes.comments.handle_reply_to_comment",
            return_value=reply,
        ),
    ):
        response = client.post(
            f"/api/posts/test-post/comments/{sample_comment.id}/reply",
            json={"text": "@Reader thanks for sharing!"},
            headers={"Authorization": "Bearer fake_token"},
        )

    assert response.status_code == 201
    data = response.get_json()
    assert data["parent_id"] == sample_comment.id


def test_post_reply_unauthenticated_returns_401(client: Any) -> None:
    """POST reply without authentication returns 401."""
    response = client.post(
        "/api/posts/test-post/comments/100/reply",
        json={"text": "Hello"},
    )
    assert response.status_code == 401


def test_delete_own_comment_returns_204(
    client: Any,
    valid_jwt_payload: dict[str, Any],
    reader_user: User,
    published_post: Post,
    sample_comment: Comment,
) -> None:
    """DELETE own comment returns 204 No Content."""
    mock_post_repo = MagicMock()
    mock_post_repo.find_by_slug.return_value = published_post

    clerk_patch, user_patch = _make_auth_patches(valid_jwt_payload, reader_user)

    with (
        clerk_patch,
        user_patch,
        patch(
            "backend.api.routes.comments._get_post_repository",
            return_value=mock_post_repo,
        ),
        patch(
            "backend.api.routes.comments._get_comment_repository",
            return_value=MagicMock(),
        ),
        patch(
            "backend.api.routes.comments.handle_delete_comment",
            return_value=True,
        ),
    ):
        response = client.delete(
            f"/api/posts/test-post/comments/{sample_comment.id}",
            headers={"Authorization": "Bearer fake_token"},
        )

    assert response.status_code == 204


def test_delete_others_comment_returns_403(
    client: Any,
    valid_jwt_payload: dict[str, Any],
    reader_user: User,
    published_post: Post,
) -> None:
    """DELETE another user's comment returns 403 Forbidden."""
    mock_post_repo = MagicMock()
    mock_post_repo.find_by_slug.return_value = published_post

    clerk_patch, user_patch = _make_auth_patches(valid_jwt_payload, reader_user)

    with (
        clerk_patch,
        user_patch,
        patch(
            "backend.api.routes.comments._get_post_repository",
            return_value=mock_post_repo,
        ),
        patch(
            "backend.api.routes.comments._get_comment_repository",
            return_value=MagicMock(),
        ),
        patch(
            "backend.api.routes.comments.handle_delete_comment",
            side_effect=AuthorizationError(
                "Cannot delete another user's comment"
            ),
        ),
    ):
        response = client.delete(
            "/api/posts/test-post/comments/999",
            headers={"Authorization": "Bearer fake_token"},
        )

    assert response.status_code == 403


def test_delete_nonexistent_comment_returns_404(
    client: Any,
    valid_jwt_payload: dict[str, Any],
    reader_user: User,
    published_post: Post,
) -> None:
    """DELETE a comment that does not exist returns 404."""
    mock_post_repo = MagicMock()
    mock_post_repo.find_by_slug.return_value = published_post

    clerk_patch, user_patch = _make_auth_patches(valid_jwt_payload, reader_user)

    with (
        clerk_patch,
        user_patch,
        patch(
            "backend.api.routes.comments._get_post_repository",
            return_value=mock_post_repo,
        ),
        patch(
            "backend.api.routes.comments._get_comment_repository",
            return_value=MagicMock(),
        ),
        patch(
            "backend.api.routes.comments.handle_delete_comment",
            side_effect=ValueError("Comment 9999 not found"),
        ),
    ):
        response = client.delete(
            "/api/posts/test-post/comments/9999",
            headers={"Authorization": "Bearer fake_token"},
        )

    assert response.status_code == 404


def test_delete_unauthenticated_returns_401(client: Any) -> None:
    """DELETE without authentication returns 401."""
    response = client.delete("/api/posts/test-post/comments/100")
    assert response.status_code == 401


def test_admin_approve_comment_returns_200(
    client: Any,
    admin_jwt_payload: dict[str, Any],
    admin_user: User,
    sample_comment: Comment,
) -> None:
    """PUT /api/admin/comments/{id}/approve returns 200 with updated comment."""
    approved = Comment(
        id=sample_comment.id,
        post_id=sample_comment.post_id,
        author_id=sample_comment.author_id,
        _text=CommentText("Great post!"),
        parent_id=None,
        created_at=sample_comment.created_at,
        updated_at=datetime(2024, 6, 2, tzinfo=UTC),
        is_deleted=False,
        is_pending_moderation=False,
    )

    clerk_patch, user_patch = _make_auth_patches(admin_jwt_payload, admin_user)

    with (
        clerk_patch,
        user_patch,
        patch(
            "backend.api.routes.comments._get_comment_repository",
            return_value=MagicMock(),
        ),
        patch(
            "backend.api.routes.comments.handle_moderate_comment",
            return_value=approved,
        ),
    ):
        response = client.put(
            f"/api/admin/comments/{sample_comment.id}/approve",
            headers={"Authorization": "Bearer fake_admin_token"},
        )

    assert response.status_code == 200
    data = response.get_json()
    assert data["is_pending_moderation"] is False


def test_admin_approve_requires_admin_role(
    client: Any,
    valid_jwt_payload: dict[str, Any],
    reader_user: User,
    sample_comment: Comment,
) -> None:
    """PUT /api/admin/comments/{id}/approve returns 403 for non-admin."""
    clerk_patch, user_patch = _make_auth_patches(valid_jwt_payload, reader_user)

    with clerk_patch, user_patch:
        response = client.put(
            f"/api/admin/comments/{sample_comment.id}/approve",
            headers={"Authorization": "Bearer fake_token"},
        )

    assert response.status_code == 403


def test_admin_delete_comment_returns_204(
    client: Any,
    admin_jwt_payload: dict[str, Any],
    admin_user: User,
    sample_comment: Comment,
) -> None:
    """DELETE /api/admin/comments/{id} returns 204 for admin."""
    clerk_patch, user_patch = _make_auth_patches(admin_jwt_payload, admin_user)

    with (
        clerk_patch,
        user_patch,
        patch(
            "backend.api.routes.comments._get_comment_repository",
            return_value=MagicMock(),
        ),
        patch(
            "backend.api.routes.comments.handle_moderate_comment",
            return_value=None,
        ),
    ):
        response = client.delete(
            f"/api/admin/comments/{sample_comment.id}",
            headers={"Authorization": "Bearer fake_admin_token"},
        )

    assert response.status_code == 204


def test_admin_delete_requires_admin_role(
    client: Any,
    valid_jwt_payload: dict[str, Any],
    reader_user: User,
    sample_comment: Comment,
) -> None:
    """DELETE /api/admin/comments/{id} returns 403 for non-admin."""
    clerk_patch, user_patch = _make_auth_patches(valid_jwt_payload, reader_user)

    with clerk_patch, user_patch:
        response = client.delete(
            f"/api/admin/comments/{sample_comment.id}",
            headers={"Authorization": "Bearer fake_token"},
        )

    assert response.status_code == 403
