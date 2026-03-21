"""Integration tests for notification preferences API endpoints.

Covers GET and PUT /api/user/notification-preferences.
Uses Flask test client with mocked infrastructure dependencies.
"""

from datetime import UTC, datetime
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from backend.domain.aggregates.notification_preferences import (
    NotificationPreferences,
)
from backend.domain.aggregates.user import User
from backend.domain.value_objects.role import Role


@pytest.fixture
def valid_jwt_payload() -> dict[str, Any]:
    """Return a valid JWT payload matching Clerk's token structure."""
    return {
        "sub": "clerk_user_123",
        "email": "user@example.com",
        "iss": "https://clerk.example.com",
        "aud": "https://api.example.com",
        "exp": 9999999999,
        "iat": 1735686000,
    }


@pytest.fixture
def authenticated_user() -> User:
    """Return an authenticated User aggregate."""
    return User(
        id=5,
        clerk_user_id="clerk_user_123",
        email="user@example.com",
        role=Role.AUTHENTICATED,
        created_at=datetime(2024, 1, 1, tzinfo=UTC),
    )


@pytest.fixture
def default_preferences(authenticated_user: User) -> NotificationPreferences:
    """Return default NotificationPreferences (all enabled)."""
    assert authenticated_user.id is not None
    return NotificationPreferences.create_defaults(authenticated_user.id)


@pytest.fixture
def partial_preferences(authenticated_user: User) -> NotificationPreferences:
    """Return NotificationPreferences with some disabled."""
    assert authenticated_user.id is not None
    return NotificationPreferences(
        user_id=authenticated_user.id,
        notify_on_comment_replies=False,
        notify_on_mentions=True,
        notify_on_new_posts=False,
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


class TestGetNotificationPreferences:
    """Tests for GET /api/user/notification-preferences."""

    def test_get_preferences_authenticated_returns_200(
        self,
        client: Any,
        valid_jwt_payload: dict[str, Any],
        authenticated_user: User,
        default_preferences: NotificationPreferences,
    ) -> None:
        """GET with valid auth returns 200 and preferences."""
        mock_prefs_repo = MagicMock()
        mock_prefs_repo.get_preferences.return_value = default_preferences
        clerk_patch, user_patch = _make_auth_patches(
            valid_jwt_payload, authenticated_user
        )

        with (
            clerk_patch,
            user_patch,
            patch(
                "backend.api.routes.notifications._get_preferences_repository",
                return_value=mock_prefs_repo,
            ),
        ):
            response = client.get(
                "/api/user/notification-preferences",
                headers={"Authorization": "Bearer fake_token"},
            )

        assert response.status_code == 200

    def test_get_preferences_returns_correct_structure(
        self,
        client: Any,
        valid_jwt_payload: dict[str, Any],
        authenticated_user: User,
        default_preferences: NotificationPreferences,
    ) -> None:
        """GET returns JSON with preferences object containing all fields."""
        mock_prefs_repo = MagicMock()
        mock_prefs_repo.get_preferences.return_value = default_preferences
        clerk_patch, user_patch = _make_auth_patches(
            valid_jwt_payload, authenticated_user
        )

        with (
            clerk_patch,
            user_patch,
            patch(
                "backend.api.routes.notifications._get_preferences_repository",
                return_value=mock_prefs_repo,
            ),
        ):
            response = client.get(
                "/api/user/notification-preferences",
                headers={"Authorization": "Bearer fake_token"},
            )

        data = response.get_json()
        assert "preferences" in data
        prefs = data["preferences"]
        assert "user_id" in prefs
        assert "notify_on_comment_replies" in prefs
        assert "notify_on_mentions" in prefs
        assert "notify_on_new_posts" in prefs

    def test_get_preferences_returns_default_values_all_true(
        self,
        client: Any,
        valid_jwt_payload: dict[str, Any],
        authenticated_user: User,
        default_preferences: NotificationPreferences,
    ) -> None:
        """GET with default preferences returns all flags as True."""
        mock_prefs_repo = MagicMock()
        mock_prefs_repo.get_preferences.return_value = default_preferences
        clerk_patch, user_patch = _make_auth_patches(
            valid_jwt_payload, authenticated_user
        )

        with (
            clerk_patch,
            user_patch,
            patch(
                "backend.api.routes.notifications._get_preferences_repository",
                return_value=mock_prefs_repo,
            ),
        ):
            response = client.get(
                "/api/user/notification-preferences",
                headers={"Authorization": "Bearer fake_token"},
            )

        prefs = response.get_json()["preferences"]
        assert prefs["notify_on_comment_replies"] is True
        assert prefs["notify_on_mentions"] is True
        assert prefs["notify_on_new_posts"] is True

    def test_get_preferences_returns_partial_disabled_preferences(
        self,
        client: Any,
        valid_jwt_payload: dict[str, Any],
        authenticated_user: User,
        partial_preferences: NotificationPreferences,
    ) -> None:
        """GET reflects existing preferences when some flags are False."""
        mock_prefs_repo = MagicMock()
        mock_prefs_repo.get_preferences.return_value = partial_preferences
        clerk_patch, user_patch = _make_auth_patches(
            valid_jwt_payload, authenticated_user
        )

        with (
            clerk_patch,
            user_patch,
            patch(
                "backend.api.routes.notifications._get_preferences_repository",
                return_value=mock_prefs_repo,
            ),
        ):
            response = client.get(
                "/api/user/notification-preferences",
                headers={"Authorization": "Bearer fake_token"},
            )

        prefs = response.get_json()["preferences"]
        assert prefs["notify_on_comment_replies"] is False
        assert prefs["notify_on_mentions"] is True
        assert prefs["notify_on_new_posts"] is False

    def test_get_preferences_calls_repo_with_current_user_id(
        self,
        client: Any,
        valid_jwt_payload: dict[str, Any],
        authenticated_user: User,
        default_preferences: NotificationPreferences,
    ) -> None:
        """GET fetches preferences for the authenticated user's id."""
        mock_prefs_repo = MagicMock()
        mock_prefs_repo.get_preferences.return_value = default_preferences
        clerk_patch, user_patch = _make_auth_patches(
            valid_jwt_payload, authenticated_user
        )

        with (
            clerk_patch,
            user_patch,
            patch(
                "backend.api.routes.notifications._get_preferences_repository",
                return_value=mock_prefs_repo,
            ),
        ):
            client.get(
                "/api/user/notification-preferences",
                headers={"Authorization": "Bearer fake_token"},
            )

        mock_prefs_repo.get_preferences.assert_called_once_with(
            authenticated_user.id
        )

    def test_get_preferences_without_auth_returns_401(
        self,
        client: Any,
    ) -> None:
        """GET without Authorization header returns 401."""
        response = client.get("/api/user/notification-preferences")

        assert response.status_code == 401

    def test_get_preferences_with_invalid_token_returns_401(
        self,
        client: Any,
    ) -> None:
        """GET with invalid token returns 401."""
        mock_clerk = MagicMock()
        mock_clerk.verify_token.side_effect = ValueError("invalid token")

        with patch(
            "backend.api.middleware.auth_middleware._get_clerk_adapter",
            return_value=mock_clerk,
        ):
            response = client.get(
                "/api/user/notification-preferences",
                headers={"Authorization": "Bearer bad_token"},
            )

        assert response.status_code == 401


class TestPutNotificationPreferences:
    """Tests for PUT /api/user/notification-preferences."""

    def test_put_preferences_with_valid_data_returns_200(
        self,
        client: Any,
        valid_jwt_payload: dict[str, Any],
        authenticated_user: User,
        default_preferences: NotificationPreferences,
    ) -> None:
        """PUT with valid body returns 200."""
        mock_prefs_repo = MagicMock()
        mock_prefs_repo.get_preferences.return_value = default_preferences
        mock_prefs_repo.update_preferences.return_value = None
        clerk_patch, user_patch = _make_auth_patches(
            valid_jwt_payload, authenticated_user
        )

        with (
            clerk_patch,
            user_patch,
            patch(
                "backend.api.routes.notifications._get_preferences_repository",
                return_value=mock_prefs_repo,
            ),
        ):
            response = client.put(
                "/api/user/notification-preferences",
                json={"notify_on_comment_replies": False},
                headers={"Authorization": "Bearer fake_token"},
            )

        assert response.status_code == 200

    def test_put_preferences_returns_updated_preferences(
        self,
        client: Any,
        valid_jwt_payload: dict[str, Any],
        authenticated_user: User,
        default_preferences: NotificationPreferences,
    ) -> None:
        """PUT returns the updated preferences in the response body."""
        mock_prefs_repo = MagicMock()
        mock_prefs_repo.get_preferences.return_value = default_preferences
        mock_prefs_repo.update_preferences.return_value = None
        clerk_patch, user_patch = _make_auth_patches(
            valid_jwt_payload, authenticated_user
        )

        with (
            clerk_patch,
            user_patch,
            patch(
                "backend.api.routes.notifications._get_preferences_repository",
                return_value=mock_prefs_repo,
            ),
        ):
            response = client.put(
                "/api/user/notification-preferences",
                json={"notify_on_comment_replies": False},
                headers={"Authorization": "Bearer fake_token"},
            )

        data = response.get_json()
        assert "preferences" in data
        assert data["preferences"]["notify_on_comment_replies"] is False

    def test_put_preferences_all_three_flags(
        self,
        client: Any,
        valid_jwt_payload: dict[str, Any],
        authenticated_user: User,
        default_preferences: NotificationPreferences,
    ) -> None:
        """PUT with all three flags updates all of them."""
        mock_prefs_repo = MagicMock()
        mock_prefs_repo.get_preferences.return_value = default_preferences
        mock_prefs_repo.update_preferences.return_value = None
        clerk_patch, user_patch = _make_auth_patches(
            valid_jwt_payload, authenticated_user
        )

        with (
            clerk_patch,
            user_patch,
            patch(
                "backend.api.routes.notifications._get_preferences_repository",
                return_value=mock_prefs_repo,
            ),
        ):
            response = client.put(
                "/api/user/notification-preferences",
                json={
                    "notify_on_comment_replies": False,
                    "notify_on_mentions": False,
                    "notify_on_new_posts": False,
                },
                headers={"Authorization": "Bearer fake_token"},
            )

        data = response.get_json()["preferences"]
        assert data["notify_on_comment_replies"] is False
        assert data["notify_on_mentions"] is False
        assert data["notify_on_new_posts"] is False

    def test_put_preferences_partial_update_leaves_other_flags_unchanged(
        self,
        client: Any,
        valid_jwt_payload: dict[str, Any],
        authenticated_user: User,
    ) -> None:
        """PUT with one flag only updates that flag; others unchanged."""
        assert authenticated_user.id is not None
        current_prefs = NotificationPreferences(
            user_id=authenticated_user.id,
            notify_on_comment_replies=True,
            notify_on_mentions=False,
            notify_on_new_posts=True,
        )
        mock_prefs_repo = MagicMock()
        mock_prefs_repo.get_preferences.return_value = current_prefs
        mock_prefs_repo.update_preferences.return_value = None
        clerk_patch, user_patch = _make_auth_patches(
            valid_jwt_payload, authenticated_user
        )

        with (
            clerk_patch,
            user_patch,
            patch(
                "backend.api.routes.notifications._get_preferences_repository",
                return_value=mock_prefs_repo,
            ),
        ):
            response = client.put(
                "/api/user/notification-preferences",
                json={"notify_on_comment_replies": False},
                headers={"Authorization": "Bearer fake_token"},
            )

        data = response.get_json()["preferences"]
        assert data["notify_on_comment_replies"] is False
        assert data["notify_on_mentions"] is False
        assert data["notify_on_new_posts"] is True

    def test_put_preferences_calls_update_with_correct_user_id(
        self,
        client: Any,
        valid_jwt_payload: dict[str, Any],
        authenticated_user: User,
        default_preferences: NotificationPreferences,
    ) -> None:
        """PUT calls update_preferences with the authenticated user's id."""
        mock_prefs_repo = MagicMock()
        mock_prefs_repo.get_preferences.return_value = default_preferences
        mock_prefs_repo.update_preferences.return_value = None
        clerk_patch, user_patch = _make_auth_patches(
            valid_jwt_payload, authenticated_user
        )

        with (
            clerk_patch,
            user_patch,
            patch(
                "backend.api.routes.notifications._get_preferences_repository",
                return_value=mock_prefs_repo,
            ),
        ):
            client.put(
                "/api/user/notification-preferences",
                json={"notify_on_mentions": False},
                headers={"Authorization": "Bearer fake_token"},
            )

        call_args = mock_prefs_repo.update_preferences.call_args
        assert call_args[0][0] == authenticated_user.id

    def test_put_preferences_without_auth_returns_401(
        self,
        client: Any,
    ) -> None:
        """PUT without Authorization header returns 401."""
        response = client.put(
            "/api/user/notification-preferences",
            json={"notify_on_comment_replies": False},
        )

        assert response.status_code == 401

    def test_put_preferences_with_no_body_returns_400(
        self,
        client: Any,
        valid_jwt_payload: dict[str, Any],
        authenticated_user: User,
    ) -> None:
        """PUT with no JSON body returns 400."""
        mock_prefs_repo = MagicMock()
        clerk_patch, user_patch = _make_auth_patches(
            valid_jwt_payload, authenticated_user
        )

        with (
            clerk_patch,
            user_patch,
            patch(
                "backend.api.routes.notifications._get_preferences_repository",
                return_value=mock_prefs_repo,
            ),
        ):
            response = client.put(
                "/api/user/notification-preferences",
                headers={"Authorization": "Bearer fake_token"},
            )

        assert response.status_code == 400

    def test_put_preferences_with_unknown_field_returns_400(
        self,
        client: Any,
        valid_jwt_payload: dict[str, Any],
        authenticated_user: User,
        default_preferences: NotificationPreferences,
    ) -> None:
        """PUT with an unrecognised field name returns 400."""
        mock_prefs_repo = MagicMock()
        mock_prefs_repo.get_preferences.return_value = default_preferences
        clerk_patch, user_patch = _make_auth_patches(
            valid_jwt_payload, authenticated_user
        )

        with (
            clerk_patch,
            user_patch,
            patch(
                "backend.api.routes.notifications._get_preferences_repository",
                return_value=mock_prefs_repo,
            ),
        ):
            response = client.put(
                "/api/user/notification-preferences",
                json={"unknown_flag": True},
                headers={"Authorization": "Bearer fake_token"},
            )

        assert response.status_code == 400

    def test_put_preferences_with_non_boolean_value_returns_400(
        self,
        client: Any,
        valid_jwt_payload: dict[str, Any],
        authenticated_user: User,
        default_preferences: NotificationPreferences,
    ) -> None:
        """PUT with a non-boolean value for a preference field returns 400."""
        mock_prefs_repo = MagicMock()
        mock_prefs_repo.get_preferences.return_value = default_preferences
        clerk_patch, user_patch = _make_auth_patches(
            valid_jwt_payload, authenticated_user
        )

        with (
            clerk_patch,
            user_patch,
            patch(
                "backend.api.routes.notifications._get_preferences_repository",
                return_value=mock_prefs_repo,
            ),
        ):
            response = client.put(
                "/api/user/notification-preferences",
                json={"notify_on_mentions": "yes"},
                headers={"Authorization": "Bearer fake_token"},
            )

        assert response.status_code == 400
