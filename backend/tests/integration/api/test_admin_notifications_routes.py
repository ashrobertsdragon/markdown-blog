"""Integration tests for admin notification history API endpoint.

Covers GET /api/admin/notifications.
Uses Flask test client with mocked infrastructure dependencies.
"""

from datetime import UTC, datetime
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from backend.domain.aggregates.notification import (
    EventType,
    Notification,
)
from backend.domain.aggregates.user import User
from backend.domain.value_objects.role import Role


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
def user_jwt_payload() -> dict[str, Any]:
    """Return a valid JWT payload for a non-admin user."""
    return {
        "sub": "clerk_user_123",
        "email": "user@example.com",
        "iss": "https://clerk.example.com",
        "aud": "https://api.example.com",
        "exp": 9999999999,
        "iat": 1735686000,
    }


@pytest.fixture
def admin_user() -> User:
    """Return an admin User aggregate."""
    return User(
        id=1,
        clerk_user_id="clerk_admin_456",
        email="admin@example.com",
        role=Role.ADMIN,
        created_at=datetime(2024, 1, 1, tzinfo=UTC),
    )


@pytest.fixture
def regular_user() -> User:
    """Return a non-admin User aggregate."""
    return User(
        id=2,
        clerk_user_id="clerk_user_123",
        email="user@example.com",
        role=Role.AUTHENTICATED,
        created_at=datetime(2024, 1, 1, tzinfo=UTC),
    )


@pytest.fixture
def sample_notification() -> Notification:
    """Return a sent Notification aggregate."""
    notif = Notification.create(
        recipient_id=5,
        sender_id=3,
        event_type=EventType.REPLY_RECEIVED,
        post_id=10,
        comment_id=42,
    )
    notif.id = 1
    notif.mark_sent("resend-test-id")
    return notif


@pytest.fixture
def pending_notification() -> Notification:
    """Return a pending Notification aggregate."""
    notif = Notification.create(
        recipient_id=5,
        sender_id=4,
        event_type=EventType.COMMENT_POSTED,
        post_id=10,
        comment_id=43,
    )
    notif.id = 2
    return notif


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


class TestGetAdminNotifications:
    """Tests for GET /api/admin/notifications."""

    def test_admin_get_notifications_returns_200(
        self,
        client: Any,
        admin_jwt_payload: dict[str, Any],
        admin_user: User,
        sample_notification: Notification,
    ) -> None:
        """GET with admin auth returns 200."""
        mock_notif_repo = MagicMock()
        mock_notif_repo.list_all_admin.return_value = [sample_notification]
        mock_notif_repo.count_all.return_value = 1
        clerk_patch, user_patch = _make_auth_patches(
            admin_jwt_payload, admin_user
        )

        with (
            clerk_patch,
            user_patch,
            patch(
                "backend.api.routes.notifications._get_notification_repository",
                return_value=mock_notif_repo,
            ),
        ):
            response = client.get(
                "/api/admin/notifications",
                headers={"Authorization": "Bearer admin_token"},
            )

        assert response.status_code == 200

    def test_admin_get_notifications_returns_correct_structure(
        self,
        client: Any,
        admin_jwt_payload: dict[str, Any],
        admin_user: User,
        sample_notification: Notification,
    ) -> None:
        """GET returns JSON with notifications list and pagination metadata."""
        mock_notif_repo = MagicMock()
        mock_notif_repo.list_all_admin.return_value = [sample_notification]
        mock_notif_repo.count_all.return_value = 1
        clerk_patch, user_patch = _make_auth_patches(
            admin_jwt_payload, admin_user
        )

        with (
            clerk_patch,
            user_patch,
            patch(
                "backend.api.routes.notifications._get_notification_repository",
                return_value=mock_notif_repo,
            ),
        ):
            response = client.get(
                "/api/admin/notifications",
                headers={"Authorization": "Bearer admin_token"},
            )

        data = response.get_json()
        assert "notifications" in data
        assert "skip" in data
        assert "limit" in data
        assert "total" in data

    def test_admin_get_notifications_serialises_notification_fields(
        self,
        client: Any,
        admin_jwt_payload: dict[str, Any],
        admin_user: User,
        sample_notification: Notification,
    ) -> None:
        """Each notification object contains all required fields."""
        mock_notif_repo = MagicMock()
        mock_notif_repo.list_all_admin.return_value = [sample_notification]
        mock_notif_repo.count_all.return_value = 1
        clerk_patch, user_patch = _make_auth_patches(
            admin_jwt_payload, admin_user
        )

        with (
            clerk_patch,
            user_patch,
            patch(
                "backend.api.routes.notifications._get_notification_repository",
                return_value=mock_notif_repo,
            ),
        ):
            response = client.get(
                "/api/admin/notifications",
                headers={"Authorization": "Bearer admin_token"},
            )

        notif = response.get_json()["notifications"][0]
        assert "id" in notif
        assert "recipient_id" in notif
        assert "sender_id" in notif
        assert "event_type" in notif
        assert "status" in notif
        assert "attempt_count" in notif
        assert "created_at" in notif

    def test_admin_get_notifications_returns_correct_total(
        self,
        client: Any,
        admin_jwt_payload: dict[str, Any],
        admin_user: User,
        sample_notification: Notification,
    ) -> None:
        """total field reflects count_all, not just the current page size."""
        mock_notif_repo = MagicMock()
        mock_notif_repo.list_all_admin.return_value = [sample_notification]
        mock_notif_repo.count_all.return_value = 127
        clerk_patch, user_patch = _make_auth_patches(
            admin_jwt_payload, admin_user
        )

        with (
            clerk_patch,
            user_patch,
            patch(
                "backend.api.routes.notifications._get_notification_repository",
                return_value=mock_notif_repo,
            ),
        ):
            response = client.get(
                "/api/admin/notifications",
                headers={"Authorization": "Bearer admin_token"},
            )

        assert response.get_json()["total"] == 127

    def test_admin_get_notifications_passes_skip_and_limit_to_repo(
        self,
        client: Any,
        admin_jwt_payload: dict[str, Any],
        admin_user: User,
    ) -> None:
        """skip and limit query params are forwarded to the repository."""
        mock_notif_repo = MagicMock()
        mock_notif_repo.list_all_admin.return_value = []
        mock_notif_repo.count_all.return_value = 0
        clerk_patch, user_patch = _make_auth_patches(
            admin_jwt_payload, admin_user
        )

        with (
            clerk_patch,
            user_patch,
            patch(
                "backend.api.routes.notifications._get_notification_repository",
                return_value=mock_notif_repo,
            ),
        ):
            client.get(
                "/api/admin/notifications?skip=20&limit=10",
                headers={"Authorization": "Bearer admin_token"},
            )

        mock_notif_repo.list_all_admin.assert_called_once_with(
            skip=20, limit=10
        )

    def test_admin_get_notifications_default_pagination(
        self,
        client: Any,
        admin_jwt_payload: dict[str, Any],
        admin_user: User,
    ) -> None:
        """Default skip=0 and limit=50 are used when not provided."""
        mock_notif_repo = MagicMock()
        mock_notif_repo.list_all_admin.return_value = []
        mock_notif_repo.count_all.return_value = 0
        clerk_patch, user_patch = _make_auth_patches(
            admin_jwt_payload, admin_user
        )

        with (
            clerk_patch,
            user_patch,
            patch(
                "backend.api.routes.notifications._get_notification_repository",
                return_value=mock_notif_repo,
            ),
        ):
            response = client.get(
                "/api/admin/notifications",
                headers={"Authorization": "Bearer admin_token"},
            )

        data = response.get_json()
        assert data["skip"] == 0
        assert data["limit"] == 50

    def test_admin_get_notifications_negative_skip_returns_400(
        self,
        client: Any,
        admin_jwt_payload: dict[str, Any],
        admin_user: User,
    ) -> None:
        """Negative skip value returns 400."""
        mock_notif_repo = MagicMock()
        clerk_patch, user_patch = _make_auth_patches(
            admin_jwt_payload, admin_user
        )

        with (
            clerk_patch,
            user_patch,
            patch(
                "backend.api.routes.notifications._get_notification_repository",
                return_value=mock_notif_repo,
            ),
        ):
            response = client.get(
                "/api/admin/notifications?skip=-1",
                headers={"Authorization": "Bearer admin_token"},
            )

        assert response.status_code == 400

    def test_admin_get_notifications_limit_over_200_returns_400(
        self,
        client: Any,
        admin_jwt_payload: dict[str, Any],
        admin_user: User,
    ) -> None:
        """limit > 200 returns 400."""
        mock_notif_repo = MagicMock()
        clerk_patch, user_patch = _make_auth_patches(
            admin_jwt_payload, admin_user
        )

        with (
            clerk_patch,
            user_patch,
            patch(
                "backend.api.routes.notifications._get_notification_repository",
                return_value=mock_notif_repo,
            ),
        ):
            response = client.get(
                "/api/admin/notifications?limit=201",
                headers={"Authorization": "Bearer admin_token"},
            )

        assert response.status_code == 400

    def test_admin_get_notifications_without_auth_returns_401(
        self,
        client: Any,
    ) -> None:
        """GET without Authorization header returns 401."""
        response = client.get("/api/admin/notifications")

        assert response.status_code == 401

    def test_admin_get_notifications_non_admin_returns_403(
        self,
        client: Any,
        user_jwt_payload: dict[str, Any],
        regular_user: User,
    ) -> None:
        """GET with authenticated (non-admin) token returns 403."""
        mock_notif_repo = MagicMock()
        clerk_patch, user_patch = _make_auth_patches(
            user_jwt_payload, regular_user
        )

        with (
            clerk_patch,
            user_patch,
            patch(
                "backend.api.routes.notifications._get_notification_repository",
                return_value=mock_notif_repo,
            ),
        ):
            response = client.get(
                "/api/admin/notifications",
                headers={"Authorization": "Bearer user_token"},
            )

        assert response.status_code == 403

    def test_admin_get_notifications_empty_list_returns_200(
        self,
        client: Any,
        admin_jwt_payload: dict[str, Any],
        admin_user: User,
    ) -> None:
        """GET with no notifications returns 200 with empty list."""
        mock_notif_repo = MagicMock()
        mock_notif_repo.list_all_admin.return_value = []
        mock_notif_repo.count_all.return_value = 0
        clerk_patch, user_patch = _make_auth_patches(
            admin_jwt_payload, admin_user
        )

        with (
            clerk_patch,
            user_patch,
            patch(
                "backend.api.routes.notifications._get_notification_repository",
                return_value=mock_notif_repo,
            ),
        ):
            response = client.get(
                "/api/admin/notifications",
                headers={"Authorization": "Bearer admin_token"},
            )

        data = response.get_json()
        assert response.status_code == 200
        assert data["notifications"] == []
        assert data["total"] == 0
