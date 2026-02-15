"""Integration tests for revisions API routes.

Tests the /posts/:slug/revisions blueprint endpoints with real Flask test
client and mocked dependencies. These tests verify the full HTTP request
flow including auth, validation, pagination, and error handling for all 4
revision management endpoints.

These tests follow TDD principles and will FAIL until routes are implemented.
"""

from datetime import UTC, datetime
from unittest.mock import MagicMock, patch
from uuid import UUID

import pytest

from backend.application.queries.compare_revisions_query import (
    CompareRevisionsResponse,
)
from backend.application.queries.get_revision_history_query import (
    GetRevisionHistoryResponse,
)
from backend.application.queries.get_revision_query import GetRevisionResponse
from backend.domain.aggregates.post import Post
from backend.domain.aggregates.post_revision import PostRevision
from backend.domain.aggregates.user import User
from backend.domain.value_objects.role import Role


@pytest.fixture
def author_user() -> User:
    """Return an author user for testing."""
    return User(
        id=10,
        clerk_user_id="clerk_author_123",
        email="author@example.com",
        role=Role.AUTHOR,
        created_at=datetime(2024, 1, 1, 12, 0, 0, tzinfo=UTC),
    )


@pytest.fixture
def admin_user() -> User:
    """Return an admin user for testing."""
    return User(
        id=20,
        clerk_user_id="clerk_admin_456",
        email="admin@example.com",
        role=Role.ADMIN,
        created_at=datetime(2024, 1, 1, 12, 0, 0, tzinfo=UTC),
    )


@pytest.fixture
def other_author_user() -> User:
    """Return a different author user for testing authorization."""
    return User(
        id=99,
        clerk_user_id="clerk_other_999",
        email="other@example.com",
        role=Role.AUTHOR,
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
def other_author_jwt_payload() -> dict[str, object]:
    """Return a valid JWT payload for another author."""
    return {
        "sub": "clerk_other_999",
        "email": "other@example.com",
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
def post_with_id() -> Post:
    """Return a published post with ID for testing revisions."""
    post = Post.create_draft(
        slug="test-post",
        title="Test Post",
        author_id=10,
    )
    post.publish("<p>Test content</p>")
    post.id = 1
    return post


@pytest.fixture
def revision_1() -> PostRevision:
    """Return first revision for testing."""
    return PostRevision.create(
        post_id=UUID("12345678-1234-5678-1234-567812345678"),
        commit_sha="abc1234567890abcdef1234567890abcdef12345",
        author_id=UUID(int=10),
        commit_message="Initial commit",
        markdown_content="# Test Post\n\nInitial content",
        is_revert=False,
    )


@pytest.fixture
def revision_2() -> PostRevision:
    """Return second revision for testing diffs."""
    return PostRevision.create(
        post_id=UUID("12345678-1234-5678-1234-567812345678"),
        commit_sha="def4567890abcdef1234567890abcdef12345678",
        author_id=UUID(int=10),
        commit_message="Update content",
        markdown_content="# Test Post\n\nUpdated content\n\nMore updates",
        is_revert=False,
    )


@pytest.fixture
def revision_3() -> PostRevision:
    """Return third revision for testing pagination."""
    return PostRevision.create(
        post_id=UUID("12345678-1234-5678-1234-567812345678"),
        commit_sha="bcd7890abcdef1234567890abcdef12345678def",
        author_id=UUID(int=10),
        commit_message="Final update",
        markdown_content="# Test Post\n\nFinal content",
        is_revert=False,
    )


class TestListRevisionsEndpoint:
    """Tests for GET /api/posts/<slug>/revisions endpoint."""

    def test_list_revisions_without_auth_returns_401(self, client):
        """GET /api/posts/:slug/revisions without auth returns 401."""
        response = client.get("/api/posts/test-post/revisions")
        assert response.status_code == 401
        assert "error" in response.json

    def test_list_revisions_with_invalid_token_returns_401(
        self, client, author_user
    ):
        """GET /api/posts/:slug/revisions with invalid token returns 401."""
        mock_clerk_adapter = MagicMock()
        mock_clerk_adapter.verify_token.side_effect = ValueError(
            "Invalid token"
        )

        with patch(
            "backend.api.middleware.auth_middleware._get_clerk_adapter",
            return_value=mock_clerk_adapter,
        ):
            response = client.get(
                "/api/posts/test-post/revisions",
                headers={"Authorization": "Bearer invalid_token"},
            )

        assert response.status_code == 401

    def test_list_revisions_returns_200_with_pagination(
        self,
        client,
        author_user,
        author_jwt_payload,
        post_with_id,
        revision_1,
        revision_2,
    ):
        """GET /api/posts/:slug/revisions returns 200 with paginated results."""
        mock_clerk_adapter = MagicMock()
        mock_clerk_adapter.verify_token.return_value = author_jwt_payload

        mock_user_repo = MagicMock()
        mock_user_repo.find_by_clerk_user_id.return_value = author_user

        mock_post_repo = MagicMock()
        mock_post_repo.find_by_slug.return_value = post_with_id

        mock_query_handler = MagicMock()
        mock_query_handler.handle.return_value = GetRevisionHistoryResponse(
            revisions=[revision_2, revision_1],
            total_count=2,
            has_more=False,
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
                "backend.api.routes.revisions._get_post_repository",
                return_value=mock_post_repo,
            ),
            patch(
                "backend.api.routes.revisions._get_revision_history_handler",
                return_value=mock_query_handler,
            ),
        ):
            response = client.get(
                "/api/posts/test-post/revisions",
                headers={"Authorization": "Bearer author_token"},
            )

        assert response.status_code == 200
        assert "revisions" in response.json
        assert isinstance(response.json["revisions"], list)
        assert len(response.json["revisions"]) == 2
        assert "total_count" in response.json
        assert response.json["total_count"] == 2
        assert "has_more" in response.json
        assert response.json["has_more"] is False

    def test_list_revisions_default_pagination(
        self,
        client,
        author_user,
        author_jwt_payload,
        post_with_id,
        revision_1,
    ):
        """GET /api/posts/:slug/revisions uses skip=0, limit=10 by default."""
        mock_clerk_adapter = MagicMock()
        mock_clerk_adapter.verify_token.return_value = author_jwt_payload

        mock_user_repo = MagicMock()
        mock_user_repo.find_by_clerk_user_id.return_value = author_user

        mock_post_repo = MagicMock()
        mock_post_repo.find_by_slug.return_value = post_with_id

        mock_query_handler = MagicMock()
        mock_query_handler.handle.return_value = GetRevisionHistoryResponse(
            revisions=[revision_1],
            total_count=1,
            has_more=False,
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
                "backend.api.routes.revisions._get_post_repository",
                return_value=mock_post_repo,
            ),
            patch(
                "backend.api.routes.revisions._get_revision_history_handler",
                return_value=mock_query_handler,
            ),
        ):
            response = client.get(
                "/api/posts/test-post/revisions",
                headers={"Authorization": "Bearer author_token"},
            )

        assert response.status_code == 200
        mock_query_handler.handle.assert_called_once()
        call_args = mock_query_handler.handle.call_args[0][0]
        assert call_args.skip == 0
        assert call_args.limit == 10

    def test_list_revisions_with_custom_skip_limit(
        self,
        client,
        author_user,
        author_jwt_payload,
        post_with_id,
        revision_1,
    ):
        """GET /api/posts/:slug/revisions?skip=5&limit=20 uses custom values."""
        mock_clerk_adapter = MagicMock()
        mock_clerk_adapter.verify_token.return_value = author_jwt_payload

        mock_user_repo = MagicMock()
        mock_user_repo.find_by_clerk_user_id.return_value = author_user

        mock_post_repo = MagicMock()
        mock_post_repo.find_by_slug.return_value = post_with_id

        mock_query_handler = MagicMock()
        mock_query_handler.handle.return_value = GetRevisionHistoryResponse(
            revisions=[revision_1],
            total_count=1,
            has_more=False,
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
                "backend.api.routes.revisions._get_post_repository",
                return_value=mock_post_repo,
            ),
            patch(
                "backend.api.routes.revisions._get_revision_history_handler",
                return_value=mock_query_handler,
            ),
        ):
            response = client.get(
                "/api/posts/test-post/revisions?skip=5&limit=20",
                headers={"Authorization": "Bearer author_token"},
            )

        assert response.status_code == 200
        call_args = mock_query_handler.handle.call_args[0][0]
        assert call_args.skip == 5
        assert call_args.limit == 20

    def test_list_revisions_skip_exceeds_maximum_returns_400(
        self, client, author_user, author_jwt_payload
    ):
        """GET with skip > 10000 returns 400."""
        mock_clerk_adapter = MagicMock()
        mock_clerk_adapter.verify_token.return_value = author_jwt_payload

        mock_user_repo = MagicMock()
        mock_user_repo.find_by_clerk_user_id.return_value = author_user

        mock_query_handler = MagicMock()
        mock_query_handler.handle.side_effect = ValueError(
            "skip must be between 0 and 10000"
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
                "backend.api.routes.revisions._get_revision_history_handler",
                return_value=mock_query_handler,
            ),
        ):
            response = client.get(
                "/api/posts/test-post/revisions?skip=10001",
                headers={"Authorization": "Bearer author_token"},
            )

        assert response.status_code == 400
        assert "error" in response.json

    def test_list_revisions_limit_exceeds_maximum_returns_400(
        self, client, author_user, author_jwt_payload
    ):
        """GET with limit > 100 returns 400."""
        mock_clerk_adapter = MagicMock()
        mock_clerk_adapter.verify_token.return_value = author_jwt_payload

        mock_user_repo = MagicMock()
        mock_user_repo.find_by_clerk_user_id.return_value = author_user

        mock_query_handler = MagicMock()
        mock_query_handler.handle.side_effect = ValueError(
            "limit must be between 1 and 100"
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
                "backend.api.routes.revisions._get_revision_history_handler",
                return_value=mock_query_handler,
            ),
        ):
            response = client.get(
                "/api/posts/test-post/revisions?limit=101",
                headers={"Authorization": "Bearer author_token"},
            )

        assert response.status_code == 400
        assert "error" in response.json

    def test_list_revisions_limit_less_than_one_returns_400(
        self, client, author_user, author_jwt_payload
    ):
        """GET with limit < 1 returns 400."""
        mock_clerk_adapter = MagicMock()
        mock_clerk_adapter.verify_token.return_value = author_jwt_payload

        mock_user_repo = MagicMock()
        mock_user_repo.find_by_clerk_user_id.return_value = author_user

        mock_query_handler = MagicMock()
        mock_query_handler.handle.side_effect = ValueError(
            "limit must be between 1 and 100"
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
                "backend.api.routes.revisions._get_revision_history_handler",
                return_value=mock_query_handler,
            ),
        ):
            response = client.get(
                "/api/posts/test-post/revisions?limit=0",
                headers={"Authorization": "Bearer author_token"},
            )

        assert response.status_code == 400
        assert "error" in response.json

    def test_list_revisions_empty_returns_200(
        self,
        client,
        author_user,
        author_jwt_payload,
        post_with_id,
    ):
        """GET /api/posts/:slug/revisions returns 200 with empty list."""
        mock_clerk_adapter = MagicMock()
        mock_clerk_adapter.verify_token.return_value = author_jwt_payload

        mock_user_repo = MagicMock()
        mock_user_repo.find_by_clerk_user_id.return_value = author_user

        mock_post_repo = MagicMock()
        mock_post_repo.find_by_slug.return_value = post_with_id

        mock_query_handler = MagicMock()
        mock_query_handler.handle.return_value = GetRevisionHistoryResponse(
            revisions=[],
            total_count=0,
            has_more=False,
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
                "backend.api.routes.revisions._get_post_repository",
                return_value=mock_post_repo,
            ),
            patch(
                "backend.api.routes.revisions._get_revision_history_handler",
                return_value=mock_query_handler,
            ),
        ):
            response = client.get(
                "/api/posts/test-post/revisions",
                headers={"Authorization": "Bearer author_token"},
            )

        assert response.status_code == 200
        assert response.json["revisions"] == []
        assert response.json["total_count"] == 0
        assert response.json["has_more"] is False

    def test_list_revisions_response_contains_revision_metadata(
        self,
        client,
        author_user,
        author_jwt_payload,
        post_with_id,
        revision_1,
    ):
        """Response includes revision metadata (message, author, timestamp)."""
        mock_clerk_adapter = MagicMock()
        mock_clerk_adapter.verify_token.return_value = author_jwt_payload

        mock_user_repo = MagicMock()
        mock_user_repo.find_by_clerk_user_id.return_value = author_user

        mock_post_repo = MagicMock()
        mock_post_repo.find_by_slug.return_value = post_with_id

        mock_query_handler = MagicMock()
        mock_query_handler.handle.return_value = GetRevisionHistoryResponse(
            revisions=[revision_1],
            total_count=1,
            has_more=False,
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
                "backend.api.routes.revisions._get_post_repository",
                return_value=mock_post_repo,
            ),
            patch(
                "backend.api.routes.revisions._get_revision_history_handler",
                return_value=mock_query_handler,
            ),
        ):
            response = client.get(
                "/api/posts/test-post/revisions",
                headers={"Authorization": "Bearer author_token"},
            )

        assert response.status_code == 200
        revisions = response.json["revisions"]
        assert len(revisions) == 1
        revision_json = revisions[0]
        assert "commit_sha" in revision_json
        assert "commit_message" in revision_json
        assert "author_id" in revision_json
        assert "created_at" in revision_json or "timestamp" in revision_json

    def test_list_revisions_most_recent_first(
        self,
        client,
        author_user,
        author_jwt_payload,
        post_with_id,
        revision_1,
        revision_2,
        revision_3,
    ):
        """Revisions are ordered with most recent first."""
        mock_clerk_adapter = MagicMock()
        mock_clerk_adapter.verify_token.return_value = author_jwt_payload

        mock_user_repo = MagicMock()
        mock_user_repo.find_by_clerk_user_id.return_value = author_user

        mock_post_repo = MagicMock()
        mock_post_repo.find_by_slug.return_value = post_with_id

        mock_query_handler = MagicMock()
        mock_query_handler.handle.return_value = GetRevisionHistoryResponse(
            revisions=[revision_3, revision_2, revision_1],
            total_count=3,
            has_more=False,
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
                "backend.api.routes.revisions._get_post_repository",
                return_value=mock_post_repo,
            ),
            patch(
                "backend.api.routes.revisions._get_revision_history_handler",
                return_value=mock_query_handler,
            ),
        ):
            response = client.get(
                "/api/posts/test-post/revisions",
                headers={"Authorization": "Bearer author_token"},
            )

        assert response.status_code == 200
        revisions = response.json["revisions"]
        assert len(revisions) == 3
        assert revisions[0]["commit_sha"] == str(revision_3.commit_sha)
        assert revisions[1]["commit_sha"] == str(revision_2.commit_sha)
        assert revisions[2]["commit_sha"] == str(revision_1.commit_sha)

    def test_list_revisions_has_more_true_when_more_exist(
        self,
        client,
        author_user,
        author_jwt_payload,
        post_with_id,
        revision_1,
    ):
        """has_more is true when more revisions exist beyond current page."""
        mock_clerk_adapter = MagicMock()
        mock_clerk_adapter.verify_token.return_value = author_jwt_payload

        mock_user_repo = MagicMock()
        mock_user_repo.find_by_clerk_user_id.return_value = author_user

        mock_post_repo = MagicMock()
        mock_post_repo.find_by_slug.return_value = post_with_id

        mock_query_handler = MagicMock()
        mock_query_handler.handle.return_value = GetRevisionHistoryResponse(
            revisions=[revision_1],
            total_count=25,
            has_more=True,
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
                "backend.api.routes.revisions._get_post_repository",
                return_value=mock_post_repo,
            ),
            patch(
                "backend.api.routes.revisions._get_revision_history_handler",
                return_value=mock_query_handler,
            ),
        ):
            response = client.get(
                "/api/posts/test-post/revisions?skip=0&limit=10",
                headers={"Authorization": "Bearer author_token"},
            )

        assert response.status_code == 200
        assert response.json["has_more"] is True
        assert response.json["total_count"] == 25

    def test_list_revisions_non_owner_returns_403(
        self,
        client,
        other_author_user,
        other_author_jwt_payload,
        post_with_id,
    ):
        """GET by non-owner (different author) returns 403."""
        mock_clerk_adapter = MagicMock()
        mock_clerk_adapter.verify_token.return_value = other_author_jwt_payload

        mock_user_repo = MagicMock()
        mock_user_repo.find_by_clerk_user_id.return_value = other_author_user

        mock_post_repo = MagicMock()
        mock_post_repo.find_by_slug.return_value = post_with_id

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
                "backend.api.routes.revisions._get_post_repository",
                return_value=mock_post_repo,
            ),
        ):
            response = client.get(
                "/api/posts/test-post/revisions",
                headers={"Authorization": "Bearer other_token"},
            )

        assert response.status_code == 403
        assert "error" in response.json
        assert "Not authorized" in response.json["error"]

    def test_list_revisions_admin_can_access_any_post(
        self,
        client,
        admin_user,
        admin_jwt_payload,
        post_with_id,
        revision_1,
    ):
        """GET by admin succeeds for any post."""
        mock_clerk_adapter = MagicMock()
        mock_clerk_adapter.verify_token.return_value = admin_jwt_payload

        mock_user_repo = MagicMock()
        mock_user_repo.find_by_clerk_user_id.return_value = admin_user

        mock_post_repo = MagicMock()
        mock_post_repo.find_by_slug.return_value = post_with_id

        mock_query_handler = MagicMock()
        mock_query_handler.handle.return_value = GetRevisionHistoryResponse(
            revisions=[revision_1],
            total_count=1,
            has_more=False,
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
                "backend.api.routes.revisions._get_post_repository",
                return_value=mock_post_repo,
            ),
            patch(
                "backend.api.routes.revisions._get_revision_history_handler",
                return_value=mock_query_handler,
            ),
        ):
            response = client.get(
                "/api/posts/test-post/revisions",
                headers={"Authorization": "Bearer admin_token"},
            )

        assert response.status_code == 200

    def test_list_revisions_owner_can_access_own_post(
        self,
        client,
        author_user,
        author_jwt_payload,
        post_with_id,
        revision_1,
    ):
        """GET by owner succeeds for own post."""
        mock_clerk_adapter = MagicMock()
        mock_clerk_adapter.verify_token.return_value = author_jwt_payload

        mock_user_repo = MagicMock()
        mock_user_repo.find_by_clerk_user_id.return_value = author_user

        mock_post_repo = MagicMock()
        mock_post_repo.find_by_slug.return_value = post_with_id

        mock_query_handler = MagicMock()
        mock_query_handler.handle.return_value = GetRevisionHistoryResponse(
            revisions=[revision_1],
            total_count=1,
            has_more=False,
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
                "backend.api.routes.revisions._get_post_repository",
                return_value=mock_post_repo,
            ),
            patch(
                "backend.api.routes.revisions._get_revision_history_handler",
                return_value=mock_query_handler,
            ),
        ):
            response = client.get(
                "/api/posts/test-post/revisions",
                headers={"Authorization": "Bearer author_token"},
            )

        assert response.status_code == 200


class TestGetSingleRevisionEndpoint:
    """Tests for GET /api/posts/<slug>/revisions/<sha> endpoint."""

    def test_get_revision_without_auth_returns_401(self, client):
        """GET /api/posts/:slug/revisions/:sha without auth returns 401."""
        response = client.get("/api/posts/test-post/revisions/abc123")
        assert response.status_code == 401
        assert "error" in response.json

    def test_get_revision_with_invalid_token_returns_401(
        self, client, author_user
    ):
        """GET with invalid token returns 401."""
        mock_clerk_adapter = MagicMock()
        mock_clerk_adapter.verify_token.side_effect = ValueError(
            "Invalid token"
        )

        with patch(
            "backend.api.middleware.auth_middleware._get_clerk_adapter",
            return_value=mock_clerk_adapter,
        ):
            response = client.get(
                "/api/posts/test-post/revisions/abc123",
                headers={"Authorization": "Bearer invalid_token"},
            )

        assert response.status_code == 401

    def test_get_revision_returns_200_with_content(
        self,
        client,
        author_user,
        author_jwt_payload,
        post_with_id,
        revision_1,
    ):
        """GET /api/posts/:slug/revisions/:sha returns 200 with content."""
        mock_clerk_adapter = MagicMock()
        mock_clerk_adapter.verify_token.return_value = author_jwt_payload

        mock_user_repo = MagicMock()
        mock_user_repo.find_by_clerk_user_id.return_value = author_user

        mock_post_repo = MagicMock()
        mock_post_repo.find_by_slug.return_value = post_with_id

        mock_revision_repo = MagicMock()
        mock_revision_repo.find_by_post_id.return_value = ([revision_1], 1)

        mock_query_handler = MagicMock()
        mock_query_handler.handle.return_value = GetRevisionResponse(
            revision=revision_1,
            markdown_content=revision_1.markdown_content,
            html_content="<h1>Test Post</h1><p>Initial content</p>",
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
                "backend.api.routes.revisions._get_post_repository",
                return_value=mock_post_repo,
            ),
            patch(
                "backend.api.routes.revisions._get_revision_repository",
                return_value=mock_revision_repo,
            ),
            patch(
                "backend.api.routes.revisions._get_revision_handler",
                return_value=mock_query_handler,
            ),
        ):
            response = client.get(
                f"/api/posts/test-post/revisions/{revision_1.commit_sha}",
                headers={"Authorization": "Bearer author_token"},
            )

        assert response.status_code == 200
        assert "commit_sha" in response.json
        assert "markdown_content" in response.json
        assert "html_content" in response.json

    def test_get_revision_includes_markdown_and_html(
        self,
        client,
        author_user,
        author_jwt_payload,
        post_with_id,
        revision_1,
    ):
        """Response includes both markdown_content and html_content."""
        mock_clerk_adapter = MagicMock()
        mock_clerk_adapter.verify_token.return_value = author_jwt_payload

        mock_user_repo = MagicMock()
        mock_user_repo.find_by_clerk_user_id.return_value = author_user

        mock_post_repo = MagicMock()
        mock_post_repo.find_by_slug.return_value = post_with_id

        mock_revision_repo = MagicMock()
        mock_revision_repo.find_by_post_id.return_value = ([revision_1], 1)

        mock_query_handler = MagicMock()
        markdown = "# Test Post\n\nInitial content"
        html = "<h1>Test Post</h1><p>Initial content</p>"
        mock_query_handler.handle.return_value = GetRevisionResponse(
            revision=revision_1,
            markdown_content=markdown,
            html_content=html,
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
                "backend.api.routes.revisions._get_post_repository",
                return_value=mock_post_repo,
            ),
            patch(
                "backend.api.routes.revisions._get_revision_repository",
                return_value=mock_revision_repo,
            ),
            patch(
                "backend.api.routes.revisions._get_revision_handler",
                return_value=mock_query_handler,
            ),
        ):
            response = client.get(
                f"/api/posts/test-post/revisions/{revision_1.commit_sha}",
                headers={"Authorization": "Bearer author_token"},
            )

        assert response.status_code == 200
        assert response.json["markdown_content"] == markdown
        assert response.json["html_content"] == html

    def test_get_revision_nonexistent_sha_returns_404(
        self,
        client,
        author_user,
        author_jwt_payload,
        post_with_id,
    ):
        """GET with non-existent SHA returns 404."""
        mock_clerk_adapter = MagicMock()
        mock_clerk_adapter.verify_token.return_value = author_jwt_payload

        mock_user_repo = MagicMock()
        mock_user_repo.find_by_clerk_user_id.return_value = author_user

        mock_post_repo = MagicMock()
        mock_post_repo.find_by_slug.return_value = post_with_id

        mock_query_handler = MagicMock()
        mock_query_handler.handle.side_effect = ValueError("Revision not found")

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
                "backend.api.routes.revisions._get_post_repository",
                return_value=mock_post_repo,
            ),
            patch(
                "backend.api.routes.revisions._get_revision_handler",
                return_value=mock_query_handler,
            ),
        ):
            response = client.get(
                "/api/posts/test-post/revisions/nonexistent123456789012345678901234567890",
                headers={"Authorization": "Bearer author_token"},
            )

        assert response.status_code == 404
        assert "error" in response.json

    def test_get_revision_invalid_sha_format_returns_400(
        self,
        client,
        author_user,
        author_jwt_payload,
        post_with_id,
    ):
        """GET with invalid SHA format returns 400."""
        mock_clerk_adapter = MagicMock()
        mock_clerk_adapter.verify_token.return_value = author_jwt_payload

        mock_user_repo = MagicMock()
        mock_user_repo.find_by_clerk_user_id.return_value = author_user

        mock_post_repo = MagicMock()
        mock_post_repo.find_by_slug.return_value = post_with_id

        mock_query_handler = MagicMock()
        mock_query_handler.handle.side_effect = ValueError("Invalid SHA format")

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
                "backend.api.routes.revisions._get_post_repository",
                return_value=mock_post_repo,
            ),
            patch(
                "backend.api.routes.revisions._get_revision_handler",
                return_value=mock_query_handler,
            ),
        ):
            response = client.get(
                "/api/posts/test-post/revisions/invalid!!!",
                headers={"Authorization": "Bearer author_token"},
            )

        assert response.status_code == 400
        assert "error" in response.json

    def test_get_revision_empty_sha_returns_400(
        self, client, author_user, author_jwt_payload
    ):
        """GET with empty SHA returns 400."""
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
            response = client.get(
                "/api/posts/test-post/revisions/",
                headers={"Authorization": "Bearer author_token"},
            )

        assert response.status_code == 404

    def test_get_revision_html_is_sanitized(
        self,
        client,
        author_user,
        author_jwt_payload,
        post_with_id,
        revision_1,
    ):
        """HTML content is sanitized (safe HTML without script tags)."""
        mock_clerk_adapter = MagicMock()
        mock_clerk_adapter.verify_token.return_value = author_jwt_payload

        mock_user_repo = MagicMock()
        mock_user_repo.find_by_clerk_user_id.return_value = author_user

        mock_post_repo = MagicMock()
        mock_post_repo.find_by_slug.return_value = post_with_id

        mock_revision_repo = MagicMock()
        mock_revision_repo.find_by_post_id.return_value = ([revision_1], 1)

        mock_query_handler = MagicMock()
        safe_html = "<h1>Test Post</h1><p>Content</p>"
        mock_query_handler.handle.return_value = GetRevisionResponse(
            revision=revision_1,
            markdown_content=revision_1.markdown_content,
            html_content=safe_html,
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
                "backend.api.routes.revisions._get_post_repository",
                return_value=mock_post_repo,
            ),
            patch(
                "backend.api.routes.revisions._get_revision_repository",
                return_value=mock_revision_repo,
            ),
            patch(
                "backend.api.routes.revisions._get_revision_handler",
                return_value=mock_query_handler,
            ),
        ):
            response = client.get(
                f"/api/posts/test-post/revisions/{revision_1.commit_sha}",
                headers={"Authorization": "Bearer author_token"},
            )

        assert response.status_code == 200
        assert response.json["html_content"] == safe_html

    def test_get_revision_includes_metadata(
        self,
        client,
        author_user,
        author_jwt_payload,
        post_with_id,
        revision_1,
    ):
        """Response includes revision metadata (author, timestamp)."""
        mock_clerk_adapter = MagicMock()
        mock_clerk_adapter.verify_token.return_value = author_jwt_payload

        mock_user_repo = MagicMock()
        mock_user_repo.find_by_clerk_user_id.return_value = author_user

        mock_post_repo = MagicMock()
        mock_post_repo.find_by_slug.return_value = post_with_id

        mock_revision_repo = MagicMock()
        mock_revision_repo.find_by_post_id.return_value = ([revision_1], 1)

        mock_query_handler = MagicMock()
        mock_query_handler.handle.return_value = GetRevisionResponse(
            revision=revision_1,
            markdown_content=revision_1.markdown_content,
            html_content="<h1>Test</h1>",
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
                "backend.api.routes.revisions._get_post_repository",
                return_value=mock_post_repo,
            ),
            patch(
                "backend.api.routes.revisions._get_revision_repository",
                return_value=mock_revision_repo,
            ),
            patch(
                "backend.api.routes.revisions._get_revision_handler",
                return_value=mock_query_handler,
            ),
        ):
            response = client.get(
                f"/api/posts/test-post/revisions/{revision_1.commit_sha}",
                headers={"Authorization": "Bearer author_token"},
            )

        assert response.status_code == 200
        assert "author_id" in response.json
        assert "timestamp" in response.json or "created_at" in response.json
        assert "commit_message" in response.json

    def test_get_revision_is_current_flag_present(
        self,
        client,
        author_user,
        author_jwt_payload,
        post_with_id,
        revision_1,
    ):
        """Response includes is_current flag for current revision status."""
        mock_clerk_adapter = MagicMock()
        mock_clerk_adapter.verify_token.return_value = author_jwt_payload

        mock_user_repo = MagicMock()
        mock_user_repo.find_by_clerk_user_id.return_value = author_user

        mock_post_repo = MagicMock()
        mock_post_repo.find_by_slug.return_value = post_with_id

        mock_revision_repo = MagicMock()
        mock_revision_repo.find_by_post_id.return_value = ([revision_1], 1)

        mock_query_handler = MagicMock()
        mock_query_handler.handle.return_value = GetRevisionResponse(
            revision=revision_1,
            markdown_content=revision_1.markdown_content,
            html_content="<h1>Test</h1>",
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
                "backend.api.routes.revisions._get_post_repository",
                return_value=mock_post_repo,
            ),
            patch(
                "backend.api.routes.revisions._get_revision_repository",
                return_value=mock_revision_repo,
            ),
            patch(
                "backend.api.routes.revisions._get_revision_handler",
                return_value=mock_query_handler,
            ),
        ):
            response = client.get(
                f"/api/posts/test-post/revisions/{revision_1.commit_sha}",
                headers={"Authorization": "Bearer author_token"},
            )

        assert response.status_code == 200
        assert "is_current" in response.json or "is_revert" in response.json

    def test_get_revision_non_owner_returns_403(
        self,
        client,
        other_author_user,
        other_author_jwt_payload,
        post_with_id,
    ):
        """GET by non-owner (different author) returns 403."""
        mock_clerk_adapter = MagicMock()
        mock_clerk_adapter.verify_token.return_value = other_author_jwt_payload

        mock_user_repo = MagicMock()
        mock_user_repo.find_by_clerk_user_id.return_value = other_author_user

        mock_post_repo = MagicMock()
        mock_post_repo.find_by_slug.return_value = post_with_id

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
                "backend.api.routes.revisions._get_post_repository",
                return_value=mock_post_repo,
            ),
        ):
            response = client.get(
                "/api/posts/test-post/revisions/abc1234567890abcdef1234567890abcdef12345",
                headers={"Authorization": "Bearer other_token"},
            )

        assert response.status_code == 403
        assert "error" in response.json
        assert "Not authorized" in response.json["error"]

    def test_get_revision_admin_can_access_any_post(
        self,
        client,
        admin_user,
        admin_jwt_payload,
        post_with_id,
        revision_1,
    ):
        """GET by admin succeeds for any post."""
        mock_clerk_adapter = MagicMock()
        mock_clerk_adapter.verify_token.return_value = admin_jwt_payload

        mock_user_repo = MagicMock()
        mock_user_repo.find_by_clerk_user_id.return_value = admin_user

        mock_post_repo = MagicMock()
        mock_post_repo.find_by_slug.return_value = post_with_id

        mock_revision_repo = MagicMock()
        mock_revision_repo.find_by_post_id.return_value = ([revision_1], 1)

        mock_query_handler = MagicMock()
        mock_query_handler.handle.return_value = GetRevisionResponse(
            revision=revision_1,
            markdown_content=revision_1.markdown_content,
            html_content="<h1>Test</h1>",
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
                "backend.api.routes.revisions._get_post_repository",
                return_value=mock_post_repo,
            ),
            patch(
                "backend.api.routes.revisions._get_revision_repository",
                return_value=mock_revision_repo,
            ),
            patch(
                "backend.api.routes.revisions._get_revision_handler",
                return_value=mock_query_handler,
            ),
        ):
            response = client.get(
                f"/api/posts/test-post/revisions/{revision_1.commit_sha}",
                headers={"Authorization": "Bearer admin_token"},
            )

        assert response.status_code == 200

    def test_get_revision_owner_can_access_own_post(
        self,
        client,
        author_user,
        author_jwt_payload,
        post_with_id,
        revision_1,
    ):
        """GET by owner succeeds for own post."""
        mock_clerk_adapter = MagicMock()
        mock_clerk_adapter.verify_token.return_value = author_jwt_payload

        mock_user_repo = MagicMock()
        mock_user_repo.find_by_clerk_user_id.return_value = author_user

        mock_post_repo = MagicMock()
        mock_post_repo.find_by_slug.return_value = post_with_id

        mock_revision_repo = MagicMock()
        mock_revision_repo.find_by_post_id.return_value = ([revision_1], 1)

        mock_query_handler = MagicMock()
        mock_query_handler.handle.return_value = GetRevisionResponse(
            revision=revision_1,
            markdown_content=revision_1.markdown_content,
            html_content="<h1>Test</h1>",
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
                "backend.api.routes.revisions._get_post_repository",
                return_value=mock_post_repo,
            ),
            patch(
                "backend.api.routes.revisions._get_revision_repository",
                return_value=mock_revision_repo,
            ),
            patch(
                "backend.api.routes.revisions._get_revision_handler",
                return_value=mock_query_handler,
            ),
        ):
            response = client.get(
                f"/api/posts/test-post/revisions/{revision_1.commit_sha}",
                headers={"Authorization": "Bearer author_token"},
            )

        assert response.status_code == 200


class TestCompareRevisionsEndpoint:
    """Tests for GET /api/posts/<slug>/revisions/<sha1>/diff/<sha2> endpoint."""

    def test_compare_revisions_without_auth_returns_401(self, client):
        """GET without auth returns 401."""
        response = client.get(
            "/api/posts/test-post/revisions/abc123/diff/def456"
        )
        assert response.status_code == 401
        assert "error" in response.json

    def test_compare_revisions_with_invalid_token_returns_401(
        self, client, author_user
    ):
        """GET with invalid token returns 401."""
        mock_clerk_adapter = MagicMock()
        mock_clerk_adapter.verify_token.side_effect = ValueError(
            "Invalid token"
        )

        with patch(
            "backend.api.middleware.auth_middleware._get_clerk_adapter",
            return_value=mock_clerk_adapter,
        ):
            response = client.get(
                "/api/posts/test-post/revisions/abc123/diff/def456",
                headers={"Authorization": "Bearer invalid_token"},
            )

        assert response.status_code == 401

    def test_compare_revisions_returns_200_with_diff(
        self,
        client,
        author_user,
        author_jwt_payload,
        post_with_id,
        revision_1,
        revision_2,
    ):
        """GET returns 200 with diff data."""
        mock_clerk_adapter = MagicMock()
        mock_clerk_adapter.verify_token.return_value = author_jwt_payload

        mock_user_repo = MagicMock()
        mock_user_repo.find_by_clerk_user_id.return_value = author_user

        mock_post_repo = MagicMock()
        mock_post_repo.find_by_slug.return_value = post_with_id

        mock_query_handler = MagicMock()
        diff_lines = [
            {"line": "# Test Post", "type": "context"},
            {"line": "Initial content", "type": "removed"},
            {"line": "Updated content", "type": "added"},
        ]
        mock_query_handler.handle.return_value = CompareRevisionsResponse(
            from_revision=revision_1,
            to_revision=revision_2,
            diff_lines=diff_lines,
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
                "backend.api.routes.revisions._get_post_repository",
                return_value=mock_post_repo,
            ),
            patch(
                "backend.api.routes.revisions._get_compare_handler",
                return_value=mock_query_handler,
            ),
        ):
            response = client.get(
                f"/api/posts/test-post/revisions/{revision_1.commit_sha}/diff/{revision_2.commit_sha}",
                headers={"Authorization": "Bearer author_token"},
            )

        assert response.status_code == 200
        assert "from_revision" in response.json
        assert "to_revision" in response.json
        assert "diff_lines" in response.json

    def test_compare_revisions_response_structure(
        self,
        client,
        author_user,
        author_jwt_payload,
        post_with_id,
        revision_1,
        revision_2,
    ):
        """Response contains correct structure with both revisions and diff."""
        mock_clerk_adapter = MagicMock()
        mock_clerk_adapter.verify_token.return_value = author_jwt_payload

        mock_user_repo = MagicMock()
        mock_user_repo.find_by_clerk_user_id.return_value = author_user

        mock_post_repo = MagicMock()
        mock_post_repo.find_by_slug.return_value = post_with_id

        mock_query_handler = MagicMock()
        diff_lines = [{"line": "test", "type": "added"}]
        mock_query_handler.handle.return_value = CompareRevisionsResponse(
            from_revision=revision_1,
            to_revision=revision_2,
            diff_lines=diff_lines,
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
                "backend.api.routes.revisions._get_post_repository",
                return_value=mock_post_repo,
            ),
            patch(
                "backend.api.routes.revisions._get_compare_handler",
                return_value=mock_query_handler,
            ),
        ):
            response = client.get(
                f"/api/posts/test-post/revisions/{revision_1.commit_sha}/diff/{revision_2.commit_sha}",
                headers={"Authorization": "Bearer author_token"},
            )

        assert response.status_code == 200
        assert isinstance(response.json["from_revision"], dict)
        assert isinstance(response.json["to_revision"], dict)
        assert isinstance(response.json["diff_lines"], list)

    def test_compare_revisions_from_sha_not_found_returns_404(
        self,
        client,
        author_user,
        author_jwt_payload,
        post_with_id,
    ):
        """GET with non-existent from_sha returns 404."""
        mock_clerk_adapter = MagicMock()
        mock_clerk_adapter.verify_token.return_value = author_jwt_payload

        mock_user_repo = MagicMock()
        mock_user_repo.find_by_clerk_user_id.return_value = author_user

        mock_post_repo = MagicMock()
        mock_post_repo.find_by_slug.return_value = post_with_id

        mock_query_handler = MagicMock()
        mock_query_handler.handle.side_effect = ValueError(
            "Source revision not found"
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
                "backend.api.routes.revisions._get_post_repository",
                return_value=mock_post_repo,
            ),
            patch(
                "backend.api.routes.revisions._get_compare_handler",
                return_value=mock_query_handler,
            ),
        ):
            response = client.get(
                "/api/posts/test-post/revisions/nonexistent1234567890abcdef1234567890abcdef/diff/def4567890abcdef1234567890abcdef12345678",
                headers={"Authorization": "Bearer author_token"},
            )

        assert response.status_code == 404
        assert "error" in response.json

    def test_compare_revisions_to_sha_not_found_returns_404(
        self,
        client,
        author_user,
        author_jwt_payload,
        post_with_id,
    ):
        """GET with non-existent to_sha returns 404."""
        mock_clerk_adapter = MagicMock()
        mock_clerk_adapter.verify_token.return_value = author_jwt_payload

        mock_user_repo = MagicMock()
        mock_user_repo.find_by_clerk_user_id.return_value = author_user

        mock_post_repo = MagicMock()
        mock_post_repo.find_by_slug.return_value = post_with_id

        mock_query_handler = MagicMock()
        mock_query_handler.handle.side_effect = ValueError(
            "Target revision not found"
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
                "backend.api.routes.revisions._get_post_repository",
                return_value=mock_post_repo,
            ),
            patch(
                "backend.api.routes.revisions._get_compare_handler",
                return_value=mock_query_handler,
            ),
        ):
            response = client.get(
                "/api/posts/test-post/revisions/abc1234567890abcdef1234567890abcdef12345/diff/nonexistent2222222222222222222222222",
                headers={"Authorization": "Bearer author_token"},
            )

        assert response.status_code == 404
        assert "error" in response.json

    def test_compare_revisions_invalid_from_sha_returns_400(
        self,
        client,
        author_user,
        author_jwt_payload,
        post_with_id,
    ):
        """GET with invalid from_sha format returns 400."""
        mock_clerk_adapter = MagicMock()
        mock_clerk_adapter.verify_token.return_value = author_jwt_payload

        mock_user_repo = MagicMock()
        mock_user_repo.find_by_clerk_user_id.return_value = author_user

        mock_post_repo = MagicMock()
        mock_post_repo.find_by_slug.return_value = post_with_id

        mock_query_handler = MagicMock()
        mock_query_handler.handle.side_effect = ValueError(
            "Invalid from_sha format"
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
                "backend.api.routes.revisions._get_post_repository",
                return_value=mock_post_repo,
            ),
            patch(
                "backend.api.routes.revisions._get_compare_handler",
                return_value=mock_query_handler,
            ),
        ):
            response = client.get(
                "/api/posts/test-post/revisions/invalid!!!/diff/abc1234567890abcdef1234567890abcdef12345",
                headers={"Authorization": "Bearer author_token"},
            )

        assert response.status_code == 400
        assert "error" in response.json

    def test_compare_revisions_invalid_to_sha_returns_400(
        self,
        client,
        author_user,
        author_jwt_payload,
        post_with_id,
    ):
        """GET with invalid to_sha format returns 400."""
        mock_clerk_adapter = MagicMock()
        mock_clerk_adapter.verify_token.return_value = author_jwt_payload

        mock_user_repo = MagicMock()
        mock_user_repo.find_by_clerk_user_id.return_value = author_user

        mock_post_repo = MagicMock()
        mock_post_repo.find_by_slug.return_value = post_with_id

        mock_query_handler = MagicMock()
        mock_query_handler.handle.side_effect = ValueError(
            "Invalid to_sha format"
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
                "backend.api.routes.revisions._get_post_repository",
                return_value=mock_post_repo,
            ),
            patch(
                "backend.api.routes.revisions._get_compare_handler",
                return_value=mock_query_handler,
            ),
        ):
            response = client.get(
                "/api/posts/test-post/revisions/abc1234567890abcdef1234567890abcdef12345/diff/invalid!!!",
                headers={"Authorization": "Bearer author_token"},
            )

        assert response.status_code == 400
        assert "error" in response.json

    def test_compare_revisions_identical_content_returns_empty_diff(
        self,
        client,
        author_user,
        author_jwt_payload,
        post_with_id,
        revision_1,
    ):
        """Comparing revision with itself returns empty diff."""
        mock_clerk_adapter = MagicMock()
        mock_clerk_adapter.verify_token.return_value = author_jwt_payload

        mock_user_repo = MagicMock()
        mock_user_repo.find_by_clerk_user_id.return_value = author_user

        mock_post_repo = MagicMock()
        mock_post_repo.find_by_slug.return_value = post_with_id

        mock_query_handler = MagicMock()
        mock_query_handler.handle.return_value = CompareRevisionsResponse(
            from_revision=revision_1,
            to_revision=revision_1,
            diff_lines=[],
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
                "backend.api.routes.revisions._get_post_repository",
                return_value=mock_post_repo,
            ),
            patch(
                "backend.api.routes.revisions._get_compare_handler",
                return_value=mock_query_handler,
            ),
        ):
            response = client.get(
                f"/api/posts/test-post/revisions/{revision_1.commit_sha}/diff/{revision_1.commit_sha}",
                headers={"Authorization": "Bearer author_token"},
            )

        assert response.status_code == 200
        assert response.json["diff_lines"] == []

    def test_compare_revisions_diff_lines_array_present(
        self,
        client,
        author_user,
        author_jwt_payload,
        post_with_id,
        revision_1,
        revision_2,
    ):
        """Response includes diff_lines array with diff content."""
        mock_clerk_adapter = MagicMock()
        mock_clerk_adapter.verify_token.return_value = author_jwt_payload

        mock_user_repo = MagicMock()
        mock_user_repo.find_by_clerk_user_id.return_value = author_user

        mock_post_repo = MagicMock()
        mock_post_repo.find_by_slug.return_value = post_with_id

        mock_query_handler = MagicMock()
        diff_lines = [
            {"line": "Initial content", "type": "removed"},
            {"line": "Updated content", "type": "added"},
        ]
        mock_query_handler.handle.return_value = CompareRevisionsResponse(
            from_revision=revision_1,
            to_revision=revision_2,
            diff_lines=diff_lines,
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
                "backend.api.routes.revisions._get_post_repository",
                return_value=mock_post_repo,
            ),
            patch(
                "backend.api.routes.revisions._get_compare_handler",
                return_value=mock_query_handler,
            ),
        ):
            response = client.get(
                f"/api/posts/test-post/revisions/{revision_1.commit_sha}/diff/{revision_2.commit_sha}",
                headers={"Authorization": "Bearer author_token"},
            )

        assert response.status_code == 200
        assert len(response.json["diff_lines"]) == 2
        assert isinstance(response.json["diff_lines"], list)

    def test_compare_revisions_non_owner_returns_403(
        self,
        client,
        other_author_user,
        other_author_jwt_payload,
        post_with_id,
    ):
        """GET by non-owner (different author) returns 403."""
        mock_clerk_adapter = MagicMock()
        mock_clerk_adapter.verify_token.return_value = other_author_jwt_payload

        mock_user_repo = MagicMock()
        mock_user_repo.find_by_clerk_user_id.return_value = other_author_user

        mock_post_repo = MagicMock()
        mock_post_repo.find_by_slug.return_value = post_with_id

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
                "backend.api.routes.revisions._get_post_repository",
                return_value=mock_post_repo,
            ),
        ):
            response = client.get(
                "/api/posts/test-post/revisions/abc123/diff/def456",
                headers={"Authorization": "Bearer other_token"},
            )

        assert response.status_code == 403
        assert "error" in response.json
        assert "Not authorized" in response.json["error"]

    def test_compare_revisions_admin_can_access_any_post(
        self,
        client,
        admin_user,
        admin_jwt_payload,
        post_with_id,
        revision_1,
        revision_2,
    ):
        """GET by admin succeeds for any post."""
        mock_clerk_adapter = MagicMock()
        mock_clerk_adapter.verify_token.return_value = admin_jwt_payload

        mock_user_repo = MagicMock()
        mock_user_repo.find_by_clerk_user_id.return_value = admin_user

        mock_post_repo = MagicMock()
        mock_post_repo.find_by_slug.return_value = post_with_id

        mock_query_handler = MagicMock()
        diff_lines = [{"line": "test", "type": "added"}]
        mock_query_handler.handle.return_value = CompareRevisionsResponse(
            from_revision=revision_1,
            to_revision=revision_2,
            diff_lines=diff_lines,
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
                "backend.api.routes.revisions._get_post_repository",
                return_value=mock_post_repo,
            ),
            patch(
                "backend.api.routes.revisions._get_compare_handler",
                return_value=mock_query_handler,
            ),
        ):
            response = client.get(
                f"/api/posts/test-post/revisions/{revision_1.commit_sha}/diff/{revision_2.commit_sha}",
                headers={"Authorization": "Bearer admin_token"},
            )

        assert response.status_code == 200

    def test_compare_revisions_owner_can_access_own_post(
        self,
        client,
        author_user,
        author_jwt_payload,
        post_with_id,
        revision_1,
        revision_2,
    ):
        """GET by owner succeeds for own post."""
        mock_clerk_adapter = MagicMock()
        mock_clerk_adapter.verify_token.return_value = author_jwt_payload

        mock_user_repo = MagicMock()
        mock_user_repo.find_by_clerk_user_id.return_value = author_user

        mock_post_repo = MagicMock()
        mock_post_repo.find_by_slug.return_value = post_with_id

        mock_query_handler = MagicMock()
        diff_lines = [{"line": "test", "type": "added"}]
        mock_query_handler.handle.return_value = CompareRevisionsResponse(
            from_revision=revision_1,
            to_revision=revision_2,
            diff_lines=diff_lines,
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
                "backend.api.routes.revisions._get_post_repository",
                return_value=mock_post_repo,
            ),
            patch(
                "backend.api.routes.revisions._get_compare_handler",
                return_value=mock_query_handler,
            ),
        ):
            response = client.get(
                f"/api/posts/test-post/revisions/{revision_1.commit_sha}/diff/{revision_2.commit_sha}",
                headers={"Authorization": "Bearer author_token"},
            )

        assert response.status_code == 200


class TestRevertEndpoint:
    """Tests for POST /api/posts/<slug>/revert endpoint."""

    def test_revert_without_auth_returns_401(self, client):
        """POST without auth returns 401."""
        response = client.post(
            "/api/posts/test-post/revert",
            json={"target_sha": "abc123"},
        )
        assert response.status_code == 401
        assert "error" in response.json

    def test_revert_with_invalid_token_returns_401(self, client):
        """POST with invalid token returns 401."""
        mock_clerk_adapter = MagicMock()
        mock_clerk_adapter.verify_token.side_effect = ValueError(
            "Invalid token"
        )

        with patch(
            "backend.api.middleware.auth_middleware._get_clerk_adapter",
            return_value=mock_clerk_adapter,
        ):
            response = client.post(
                "/api/posts/test-post/revert",
                headers={"Authorization": "Bearer invalid_token"},
                json={"target_sha": "abc123"},
            )

        assert response.status_code == 401

    def test_revert_by_non_author_returns_403(
        self,
        client,
        regular_user,
        regular_jwt_payload,
        post_with_id,
    ):
        """POST by non-author/non-admin returns 403."""
        mock_clerk_adapter = MagicMock()
        mock_clerk_adapter.verify_token.return_value = regular_jwt_payload

        mock_user_repo = MagicMock()
        mock_user_repo.find_by_clerk_user_id.return_value = regular_user

        mock_post_repo = MagicMock()
        mock_post_repo.find_by_slug.return_value = post_with_id

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
                "backend.api.routes.revisions._get_post_repository",
                return_value=mock_post_repo,
            ),
        ):
            response = client.post(
                "/api/posts/test-post/revert",
                headers={"Authorization": "Bearer user_token"},
                json={"target_sha": "abc1234567890abcdef1234567890abcdef12345"},
            )

        assert response.status_code == 403
        assert "error" in response.json

    def test_revert_by_different_author_returns_403(
        self,
        client,
        other_author_user,
        other_author_jwt_payload,
        post_with_id,
    ):
        """POST by different author returns 403."""
        mock_clerk_adapter = MagicMock()
        mock_clerk_adapter.verify_token.return_value = other_author_jwt_payload

        mock_user_repo = MagicMock()
        mock_user_repo.find_by_clerk_user_id.return_value = other_author_user

        mock_post_repo = MagicMock()
        mock_post_repo.find_by_slug.return_value = post_with_id

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
                "backend.api.routes.revisions._get_post_repository",
                return_value=mock_post_repo,
            ),
        ):
            response = client.post(
                "/api/posts/test-post/revert",
                headers={"Authorization": "Bearer other_token"},
                json={"target_sha": "abc1234567890abcdef1234567890abcdef12345"},
            )

        assert response.status_code == 403
        assert "error" in response.json

    def test_revert_by_admin_succeeds(
        self,
        client,
        admin_user,
        admin_jwt_payload,
        post_with_id,
        revision_1,
    ):
        """POST by admin should succeed regardless of post author."""
        mock_clerk_adapter = MagicMock()
        mock_clerk_adapter.verify_token.return_value = admin_jwt_payload

        mock_user_repo = MagicMock()
        mock_user_repo.find_by_clerk_user_id.return_value = admin_user

        mock_post_repo = MagicMock()
        mock_post_repo.find_by_slug.return_value = post_with_id

        revert_revision = PostRevision.create(
            post_id=UUID("12345678-1234-5678-1234-567812345678"),
            commit_sha="abcdef1234567890abcdef1234567890abcdef12",
            author_id=UUID(int=20),
            commit_message="Revert to abc123",
            markdown_content="# Test Post\n\nInitial content",
            is_revert=True,
        )

        mock_handler = MagicMock()
        mock_handler.handle.return_value = revert_revision

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
                "backend.api.routes.revisions._get_post_repository",
                return_value=mock_post_repo,
            ),
            patch(
                "backend.api.routes.revisions._get_revert_handler",
                return_value=mock_handler,
            ),
        ):
            response = client.post(
                "/api/posts/test-post/revert",
                headers={"Authorization": "Bearer admin_token"},
                json={"target_sha": "abc1234567890abcdef1234567890abcdef12345"},
            )

        assert response.status_code == 200

    def test_revert_by_post_owner_succeeds(
        self,
        client,
        author_user,
        author_jwt_payload,
        post_with_id,
        revision_1,
    ):
        """POST by post owner should succeed."""
        mock_clerk_adapter = MagicMock()
        mock_clerk_adapter.verify_token.return_value = author_jwt_payload

        mock_user_repo = MagicMock()
        mock_user_repo.find_by_clerk_user_id.return_value = author_user

        mock_post_repo = MagicMock()
        mock_post_repo.find_by_slug.return_value = post_with_id

        revert_revision = PostRevision.create(
            post_id=UUID("12345678-1234-5678-1234-567812345678"),
            commit_sha="abcdef1234567890abcdef1234567890abcdef12",
            author_id=UUID(int=10),
            commit_message="Revert to abc123",
            markdown_content="# Test Post\n\nInitial content",
            is_revert=True,
        )

        mock_handler = MagicMock()
        mock_handler.handle.return_value = revert_revision

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
                "backend.api.routes.revisions._get_post_repository",
                return_value=mock_post_repo,
            ),
            patch(
                "backend.api.routes.revisions._get_revert_handler",
                return_value=mock_handler,
            ),
        ):
            response = client.post(
                "/api/posts/test-post/revert",
                headers={"Authorization": "Bearer author_token"},
                json={"target_sha": "abc1234567890abcdef1234567890abcdef12345"},
            )

        assert response.status_code == 200

    def test_revert_target_sha_not_found_returns_404(
        self, client, author_user, author_jwt_payload
    ):
        """POST with non-existent target_sha returns 404."""
        mock_clerk_adapter = MagicMock()
        mock_clerk_adapter.verify_token.return_value = author_jwt_payload

        mock_user_repo = MagicMock()
        mock_user_repo.find_by_clerk_user_id.return_value = author_user

        mock_handler = MagicMock()
        mock_handler.handle.side_effect = ValueError("Revision not found")

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
                "backend.api.routes.revisions._get_revert_handler",
                return_value=mock_handler,
            ),
        ):
            response = client.post(
                "/api/posts/test-post/revert",
                headers={"Authorization": "Bearer author_token"},
                json={"target_sha": "nonexistent"},
            )

        assert response.status_code == 404
        assert "error" in response.json

    def test_revert_post_not_found_returns_404(
        self, client, author_user, author_jwt_payload
    ):
        """POST for non-existent post returns 404."""
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
                "backend.api.routes.revisions._get_revert_handler",
                return_value=mock_handler,
            ),
        ):
            response = client.post(
                "/api/posts/nonexistent/revert",
                headers={"Authorization": "Bearer author_token"},
                json={"target_sha": "abc123"},
            )

        assert response.status_code == 404
        assert "error" in response.json

    def test_revert_invalid_sha_format_returns_400(
        self, client, author_user, author_jwt_payload
    ):
        """POST with invalid SHA format returns 400."""
        mock_clerk_adapter = MagicMock()
        mock_clerk_adapter.verify_token.return_value = author_jwt_payload

        mock_user_repo = MagicMock()
        mock_user_repo.find_by_clerk_user_id.return_value = author_user

        mock_handler = MagicMock()
        mock_handler.handle.side_effect = ValueError("Invalid SHA format")

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
                "backend.api.routes.revisions._get_revert_handler",
                return_value=mock_handler,
            ),
        ):
            response = client.post(
                "/api/posts/test-post/revert",
                headers={"Authorization": "Bearer author_token"},
                json={"target_sha": "invalid!!!"},
            )

        assert response.status_code == 400
        assert "error" in response.json

    def test_revert_empty_target_sha_returns_400(
        self, client, author_user, author_jwt_payload
    ):
        """POST with empty target_sha returns 400."""
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
                "/api/posts/test-post/revert",
                headers={"Authorization": "Bearer author_token"},
                json={"target_sha": ""},
            )

        assert response.status_code == 400
        assert "error" in response.json

    def test_revert_success_returns_new_commit_sha(
        self,
        client,
        author_user,
        author_jwt_payload,
        post_with_id,
    ):
        """Successful revert returns new_commit_sha in response."""
        mock_clerk_adapter = MagicMock()
        mock_clerk_adapter.verify_token.return_value = author_jwt_payload

        mock_user_repo = MagicMock()
        mock_user_repo.find_by_clerk_user_id.return_value = author_user

        mock_post_repo = MagicMock()
        mock_post_repo.find_by_slug.return_value = post_with_id

        new_sha = "abcdef1234567890abcdef1234567890abcdef12"
        revert_revision = PostRevision.create(
            post_id=UUID("12345678-1234-5678-1234-567812345678"),
            commit_sha=new_sha,
            author_id=UUID(int=10),
            commit_message="Revert to abc123",
            markdown_content="# Test Post\n\nInitial content",
            is_revert=True,
        )

        mock_handler = MagicMock()
        mock_handler.handle.return_value = revert_revision

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
                "backend.api.routes.revisions._get_post_repository",
                return_value=mock_post_repo,
            ),
            patch(
                "backend.api.routes.revisions._get_revert_handler",
                return_value=mock_handler,
            ),
        ):
            response = client.post(
                "/api/posts/test-post/revert",
                headers={"Authorization": "Bearer author_token"},
                json={"target_sha": "abc1234567890abcdef1234567890abcdef12345"},
            )

        assert response.status_code == 200
        assert (
            "new_commit_sha" in response.json or "commit_sha" in response.json
        )

    def test_revert_success_returns_redirect_url(
        self,
        client,
        author_user,
        author_jwt_payload,
        post_with_id,
    ):
        """Successful revert returns redirect_url in response."""
        mock_clerk_adapter = MagicMock()
        mock_clerk_adapter.verify_token.return_value = author_jwt_payload

        mock_user_repo = MagicMock()
        mock_user_repo.find_by_clerk_user_id.return_value = author_user

        mock_post_repo = MagicMock()
        mock_post_repo.find_by_slug.return_value = post_with_id

        revert_revision = PostRevision.create(
            post_id=UUID("12345678-1234-5678-1234-567812345678"),
            commit_sha="abcdef1234567890abcdef1234567890abcdef12",
            author_id=UUID(int=10),
            commit_message="Revert to abc123",
            markdown_content="# Test Post\n\nInitial content",
            is_revert=True,
        )

        mock_handler = MagicMock()
        mock_handler.handle.return_value = revert_revision

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
                "backend.api.routes.revisions._get_post_repository",
                return_value=mock_post_repo,
            ),
            patch(
                "backend.api.routes.revisions._get_revert_handler",
                return_value=mock_handler,
            ),
        ):
            response = client.post(
                "/api/posts/test-post/revert",
                headers={"Authorization": "Bearer author_token"},
                json={"target_sha": "abc1234567890abcdef1234567890abcdef12345"},
            )

        assert response.status_code == 200
        assert "redirect_url" in response.json or "success" in response.json

    def test_revert_creates_new_revision_with_is_revert_flag(
        self,
        client,
        author_user,
        author_jwt_payload,
        post_with_id,
    ):
        """Revert creates PostRevision with is_revert=True."""
        mock_clerk_adapter = MagicMock()
        mock_clerk_adapter.verify_token.return_value = author_jwt_payload

        mock_user_repo = MagicMock()
        mock_user_repo.find_by_clerk_user_id.return_value = author_user

        mock_post_repo = MagicMock()
        mock_post_repo.find_by_slug.return_value = post_with_id

        revert_revision = PostRevision.create(
            post_id=UUID("12345678-1234-5678-1234-567812345678"),
            commit_sha="abcdef1234567890abcdef1234567890abcdef12",
            author_id=UUID(int=10),
            commit_message="Revert to abc123",
            markdown_content="# Test Post\n\nInitial content",
            is_revert=True,
        )

        mock_handler = MagicMock()
        mock_handler.handle.return_value = revert_revision

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
                "backend.api.routes.revisions._get_post_repository",
                return_value=mock_post_repo,
            ),
            patch(
                "backend.api.routes.revisions._get_revert_handler",
                return_value=mock_handler,
            ),
        ):
            response = client.post(
                "/api/posts/test-post/revert",
                headers={"Authorization": "Bearer author_token"},
                json={"target_sha": "abc1234567890abcdef1234567890abcdef12345"},
            )

        assert response.status_code == 200
        if "revision" in response.json:
            assert response.json["revision"]["is_revert"] is True

    def test_revert_missing_target_sha_returns_400(
        self, client, author_user, author_jwt_payload
    ):
        """POST without target_sha field returns 400."""
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
                "/api/posts/test-post/revert",
                headers={"Authorization": "Bearer author_token"},
                json={},
            )

        assert response.status_code == 400
        assert "error" in response.json

    def test_revert_non_destructive_original_revision_visible(
        self,
        client,
        author_user,
        author_jwt_payload,
        post_with_id,
    ):
        """Revert is non-destructive: original revision remains visible."""
        mock_clerk_adapter = MagicMock()
        mock_clerk_adapter.verify_token.return_value = author_jwt_payload

        mock_user_repo = MagicMock()
        mock_user_repo.find_by_clerk_user_id.return_value = author_user

        mock_post_repo = MagicMock()
        mock_post_repo.find_by_slug.return_value = post_with_id

        revert_revision = PostRevision.create(
            post_id=UUID("12345678-1234-5678-1234-567812345678"),
            commit_sha="abcdef1234567890abcdef1234567890abcdef12",
            author_id=UUID(int=10),
            commit_message="Revert to abc123",
            markdown_content="# Test Post\n\nInitial content",
            is_revert=True,
        )

        mock_handler = MagicMock()
        mock_handler.handle.return_value = revert_revision

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
                "backend.api.routes.revisions._get_post_repository",
                return_value=mock_post_repo,
            ),
            patch(
                "backend.api.routes.revisions._get_revert_handler",
                return_value=mock_handler,
            ),
        ):
            response = client.post(
                "/api/posts/test-post/revert",
                headers={"Authorization": "Bearer author_token"},
                json={"target_sha": "abc1234567890abcdef1234567890abcdef12345"},
            )

        assert response.status_code == 200
