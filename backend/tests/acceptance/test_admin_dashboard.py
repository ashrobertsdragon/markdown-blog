"""Acceptance tests for Admin Dashboard spec based on requirements.md.

These tests verify admin user management, content moderation, system health
monitoring, and dashboard navigation, ensuring alignment with the Acceptance
Criteria in @.spec-workflow/specs/admin-dashboard/requirements.md.
"""

from datetime import UTC, datetime
from typing import Any, Protocol, cast

import pytest
from flask.testing import FlaskClient

import backend.api.routes.admin
from backend.domain.aggregates.user import User
from backend.domain.value_objects.role import Role
from backend.infrastructure.persistence.post_repository import PostRepository
from backend.infrastructure.persistence.user_repository import UserRepository

_AUTH_HEADER = {"Authorization": "Bearer test-token"}


class _Resp(Protocol):
    """Structural type for Flask test client responses."""

    status_code: int
    json: Any
    headers: Any


def _get(client: FlaskClient, url: str, **kw: Any) -> _Resp:
    """Make a typed GET request."""
    return cast(_Resp, client.get(url, **kw))


def _post(client: FlaskClient, url: str, **kw: Any) -> _Resp:
    """Make a typed POST request."""
    return cast(_Resp, client.post(url, **kw))


def _delete(client: FlaskClient, url: str, **kw: Any) -> _Resp:
    """Make a typed DELETE request."""
    return cast(_Resp, client.delete(url, **kw))


def _put(client: FlaskClient, url: str, **kw: Any) -> _Resp:
    """Make a typed PUT request."""
    return cast(_Resp, client.put(url, **kw))


def _make_user(
    clerk_id: str,
    email: str,
    role: Role = Role.AUTHENTICATED,
) -> User:
    """Construct a transient User aggregate ready for persistence."""
    return User(
        id=None,
        clerk_user_id=clerk_id,
        email=email,
        role=role,
        created_at=datetime.now(UTC),
    )


@pytest.fixture(autouse=True)
def reset_admin_singletons(monkeypatch: pytest.MonkeyPatch) -> None:
    """Reset module-level singletons in admin.py before each test.

    The client fixture resets singletons in posts/comments routes but not in
    admin.py. Without this, a cached repository from a previous test would
    hold a connection to the disposed engine, causing 500 errors on the next
    test.
    """
    monkeypatch.setattr(backend.api.routes.admin, "_post_repository", None)
    monkeypatch.setattr(backend.api.routes.admin, "_comment_repository", None)
    monkeypatch.setattr(backend.api.routes.admin, "_user_repository", None)
    monkeypatch.setattr(backend.api.routes.admin, "_draft_repository", None)
    monkeypatch.setattr(backend.api.routes.admin, "_filesystem_settings", None)


@pytest.mark.usefixtures("mock_clerk_auth_admin")
def test_user_management_interface(
    client: FlaskClient,
    auth_context: Any,
    reader_user: User,
    reader_jwt_payload: dict[str, object],
) -> None:
    """Test admins can view all users and update roles via the API.

    Acceptance Criteria:
    - Admin visits /admin/users: all users displayed with email, role, created_at
    - Admin selects new role and confirms: user's role updated via PUT /api/admin/users/:id/role
    - Role update succeeds: response contains updated role
    - Non-admin request to list users: 403 Forbidden
    """
    repo = UserRepository()
    alice = repo.save(_make_user("ck_alice", "alice@example.com"))
    repo.save(_make_user("ck_bob", "bob@example.com"))

    list_resp = _get(client, "/api/admin/users", headers=_AUTH_HEADER)
    assert list_resp.status_code == 200
    data = list_resp.json
    assert "users" in data
    assert "total_count" in data
    assert data["total_count"] >= 2

    emails = [u["email"] for u in data["users"]]
    assert "alice@example.com" in emails
    assert "bob@example.com" in emails

    for user in data["users"]:
        assert "id" in user
        assert "email" in user
        assert "role" in user
        assert "created_at" in user

    role_resp = _put(
        client,
        f"/api/admin/users/{alice.id}/role",
        headers=_AUTH_HEADER,
        json={"role": "admin"},
    )
    assert role_resp.status_code == 200
    updated = role_resp.json
    assert updated["role"] == "admin"
    assert updated["email"] == "alice@example.com"

    with auth_context(reader_user, reader_jwt_payload):
        forbidden_resp = _get(client, "/api/admin/users", headers=_AUTH_HEADER)
    assert forbidden_resp.status_code == 403


@pytest.mark.usefixtures("mock_clerk_auth_admin")
def test_user_profile_viewer(
    client: FlaskClient,
) -> None:
    """Test admins can view activity summaries for individual users.

    Acceptance Criteria:
    - Admin clicks user's email: profile page shows user details and recent activity
    - Profile loads: shows posts_count, comments_count, recent_posts, recent_comments
    - User not found: 404 returned
    """
    repo = UserRepository()
    user = repo.save(_make_user("ck_profile_test", "profile@example.com"))

    profile_resp = _get(
        client,
        f"/api/admin/users/{user.id}",
        headers=_AUTH_HEADER,
    )
    assert profile_resp.status_code == 200
    profile = profile_resp.json
    assert profile["id"] == user.id
    assert profile["email"] == "profile@example.com"
    assert "role" in profile
    assert "created_at" in profile
    assert "clerk_id" not in profile

    activity_resp = _get(
        client,
        f"/api/admin/users/{user.id}/activity",
        headers=_AUTH_HEADER,
    )
    assert activity_resp.status_code == 200
    data = activity_resp.json
    assert data["user_id"] == user.id
    assert "posts_count" in data
    assert "comments_count" in data
    assert "recent_posts" in data
    assert "recent_comments" in data
    assert isinstance(data["recent_posts"], list)
    assert isinstance(data["recent_comments"], list)

    not_found_resp = _get(
        client, "/api/admin/users/99999/activity", headers=_AUTH_HEADER
    )
    assert not_found_resp.status_code == 404

    user_not_found_resp = _get(
        client, "/api/admin/users/99999", headers=_AUTH_HEADER
    )
    assert user_not_found_resp.status_code == 404


@pytest.mark.usefixtures("mock_clerk_auth_admin")
def test_content_moderation_dashboard(
    client: FlaskClient,
    auth_context: Any,
    author_user: User,
    author_jwt_payload: dict[str, object],
    reader_user: User,
    reader_jwt_payload: dict[str, object],
) -> None:
    """Test admins can list published posts, unpublish them, and delete comments.

    Acceptance Criteria:
    - Admin visits /admin/content: Published Posts and Recent Comments listed
    - Admin unpublishes post: POST /api/admin/posts/:id/unpublish returns 200
    - Admin deletes comment: DELETE /api/admin/comments/:id returns 204
    """
    slug = "admin-moderation-test"

    with auth_context(author_user, author_jwt_payload):
        create_resp = _post(
            client,
            "/api/posts",
            headers=_AUTH_HEADER,
            json={"slug": slug, "title": "Moderation Test Post"},
        )
        assert create_resp.status_code == 201

        publish_resp = _post(
            client,
            f"/api/posts/{slug}/publish",
            headers=_AUTH_HEADER,
        )
        assert publish_resp.status_code == 200

    post = PostRepository().find_by_slug(slug)
    assert post is not None
    post_id = post.id

    posts_resp = _get(client, "/api/admin/posts", headers=_AUTH_HEADER)
    assert posts_resp.status_code == 200
    posts_data = posts_resp.json
    assert "posts" in posts_data
    assert "total_count" in posts_data
    post_ids = [p["id"] for p in posts_data["posts"]]
    assert post_id in post_ids

    unpublish_resp = _post(
        client,
        f"/api/admin/posts/{post_id}/unpublish",
        headers=_AUTH_HEADER,
    )
    assert unpublish_resp.status_code == 200
    assert unpublish_resp.json["message"] == "Post unpublished"

    with auth_context(reader_user, reader_jwt_payload):
        republish_resp = _post(
            client,
            f"/api/posts/{slug}/publish",
            headers=_AUTH_HEADER,
        )
        assert republish_resp.status_code == 403

    with auth_context(author_user, author_jwt_payload):
        republish_author_resp = _post(
            client,
            f"/api/posts/{slug}/publish",
            headers=_AUTH_HEADER,
        )
        assert republish_author_resp.status_code == 200

    with auth_context(reader_user, reader_jwt_payload):
        comment_resp = _post(
            client,
            f"/api/posts/{slug}/comments",
            headers=_AUTH_HEADER,
            json={"text": "Comment for admin deletion."},
        )
        assert comment_resp.status_code == 201
        comment_id = comment_resp.json["id"]

    comments_resp = _get(client, "/api/admin/comments", headers=_AUTH_HEADER)
    assert comments_resp.status_code == 200
    comments_data = comments_resp.json
    assert "comments" in comments_data
    assert "total_count" in comments_data

    delete_resp = _delete(
        client,
        f"/api/admin/comments/{comment_id}",
        headers=_AUTH_HEADER,
    )
    assert delete_resp.status_code == 204


@pytest.mark.usefixtures("mock_clerk_auth_admin")
def test_system_health_dashboard(
    client: FlaskClient,
    auth_context: Any,
    reader_user: User,
    reader_jwt_payload: dict[str, object],
) -> None:
    """Test admins can view system health metrics and recent error logs.

    Acceptance Criteria:
    - Admin visits /admin/system: health metrics displayed (status, database, uptime)
    - Health check returns 200: response has status and uptime_seconds fields
    - Admin clicks "Recent Errors": last N application errors returned
    - Non-admin request to health endpoint: 403 Forbidden
    """
    health_resp = _get(client, "/api/admin/system/health", headers=_AUTH_HEADER)
    assert health_resp.status_code == 200
    health_data = health_resp.json
    assert "status" in health_data
    assert "uptime_seconds" in health_data
    assert "database" in health_data

    errors_resp = _get(client, "/api/admin/system/errors", headers=_AUTH_HEADER)
    assert errors_resp.status_code == 200
    errors_data = errors_resp.json
    assert "errors" in errors_data
    assert isinstance(errors_data["errors"], list)
    assert "total_count" in errors_data

    with auth_context(reader_user, reader_jwt_payload):
        forbidden_resp = _get(
            client, "/api/admin/system/health", headers=_AUTH_HEADER
        )
    assert forbidden_resp.status_code == 403


@pytest.mark.usefixtures("mock_clerk_auth_admin")
def test_admin_dashboard_navigation(
    client: FlaskClient,
    auth_context: Any,
    reader_user: User,
    reader_jwt_payload: dict[str, object],
) -> None:
    """Test admin SPA routes are served and authorization is enforced.

    Acceptance Criteria:
    - Admin visits /admin: SPA index.html served (200)
    - Admin visits /admin/users sub-route: SPA catch-all serves index.html
    - Unauthenticated request to admin API: 401 Unauthorized
    - Authenticated non-admin request to admin API: 403 Forbidden
    """
    spa_root_resp = _get(client, "/admin")
    assert spa_root_resp.status_code == 200

    spa_users_resp = _get(client, "/admin/users")
    assert spa_users_resp.status_code == 200

    no_auth_resp = _get(client, "/api/admin/users")
    assert no_auth_resp.status_code == 401

    with auth_context(reader_user, reader_jwt_payload):
        reader_resp = _get(client, "/api/admin/users", headers=_AUTH_HEADER)
    assert reader_resp.status_code == 403


@pytest.mark.usefixtures("mock_clerk_auth_admin")
def test_admin_dashboard_layout(
    client: FlaskClient,
) -> None:
    """Test admin SPA sub-routes are served and admin API responses are JSON.

    Acceptance Criteria:
    - Admin visits /admin/content: SPA catch-all serves index.html (200)
    - Admin visits /admin/system: SPA catch-all serves index.html (200)
    - All admin API endpoints return application/json content-type
    """
    content_resp = _get(client, "/admin/content")
    assert content_resp.status_code == 200

    system_resp = _get(client, "/admin/system")
    assert system_resp.status_code == 200

    api_endpoints = [
        "/api/admin/users",
        "/api/admin/posts",
        "/api/admin/comments",
        "/api/admin/system/health",
        "/api/admin/system/errors",
    ]
    for endpoint in api_endpoints:
        resp = _get(client, endpoint, headers=_AUTH_HEADER)
        assert resp.status_code == 200, (
            f"Expected 200 from {endpoint}, got {resp.status_code}"
        )
        content_type = resp.headers.get("Content-Type", "")
        assert "application/json" in content_type, (
            f"{endpoint} did not return JSON; Content-Type was {content_type!r}"
        )


@pytest.mark.usefixtures("mock_clerk_auth_admin")
def test_admin_api_endpoints(
    client: FlaskClient,
    auth_context: Any,
    reader_user: User,
    reader_jwt_payload: dict[str, object],
) -> None:
    """Comprehensive test of all admin API endpoints with proper authorization.

    Acceptance Criteria:
    - GET /api/admin/users: 200 with users list
    - PUT /api/admin/users/:id/role: 200 on valid user
    - GET /api/admin/users/:id/activity: 200 on valid user
    - GET /api/admin/system/health: 200 with status field
    - GET /api/admin/system/errors: 200 with errors and total_count
    - GET /api/admin/posts: 200 with posts list
    - GET /api/admin/comments: 200 with comments list
    - Non-admin request to any admin endpoint: 403
    """
    repo = UserRepository()
    target = repo.save(_make_user("ck_endpoint_test", "endpoint@example.com"))
    target_id = target.id

    users_resp = _get(client, "/api/admin/users", headers=_AUTH_HEADER)
    assert users_resp.status_code == 200
    assert "users" in users_resp.json
    assert "total_count" in users_resp.json

    role_resp = _put(
        client,
        f"/api/admin/users/{target_id}/role",
        headers=_AUTH_HEADER,
        json={"role": "authenticated"},
    )
    assert role_resp.status_code == 200
    assert role_resp.json["role"] == "authenticated"

    activity_resp = _get(
        client,
        f"/api/admin/users/{target_id}/activity",
        headers=_AUTH_HEADER,
    )
    assert activity_resp.status_code == 200
    assert "user_id" in activity_resp.json

    health_resp = _get(client, "/api/admin/system/health", headers=_AUTH_HEADER)
    assert health_resp.status_code == 200
    assert "status" in health_resp.json

    errors_resp = _get(client, "/api/admin/system/errors", headers=_AUTH_HEADER)
    assert errors_resp.status_code == 200
    assert "errors" in errors_resp.json
    assert "total_count" in errors_resp.json

    posts_resp = _get(client, "/api/admin/posts", headers=_AUTH_HEADER)
    assert posts_resp.status_code == 200
    assert "posts" in posts_resp.json

    comments_resp = _get(client, "/api/admin/comments", headers=_AUTH_HEADER)
    assert comments_resp.status_code == 200
    assert "comments" in comments_resp.json

    with auth_context(reader_user, reader_jwt_payload):
        non_admin_resp = _get(client, "/api/admin/users", headers=_AUTH_HEADER)
    assert non_admin_resp.status_code == 403
