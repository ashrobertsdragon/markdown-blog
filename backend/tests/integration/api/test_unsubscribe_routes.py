"""Integration tests for the unsubscribe API endpoint.

Covers GET /api/unsubscribe.
Uses Flask test client with mocked infrastructure dependencies.
Token verification is tested by patching the utility function directly.
"""

import hmac
from datetime import UTC, datetime
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from backend.domain.aggregates.user import User
from backend.domain.value_objects.role import Role

_TEST_SECRET = "test-unsubscribe-secret"


def _make_valid_token(user_id: int) -> str:
    """Generate a valid unsubscribe token matching the test secret."""
    return hmac.new(
        _TEST_SECRET.encode(), f"{user_id}".encode(), "sha256"
    ).hexdigest()


@pytest.fixture
def target_user() -> User:
    """Return a User aggregate to be unsubscribed."""
    return User(
        id=7,
        clerk_user_id="clerk_user_789",
        email="target@example.com",
        role=Role.AUTHENTICATED,
        created_at=datetime(2024, 1, 1, tzinfo=UTC),
    )


class TestGetUnsubscribe:
    """Tests for GET /api/unsubscribe."""

    def test_unsubscribe_with_valid_token_returns_200(
        self,
        client: Any,
        target_user: User,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """GET with valid user_id and token returns 200."""
        monkeypatch.setenv("UNSUBSCRIBE_SECRET", _TEST_SECRET)
        assert target_user.id is not None
        token = _make_valid_token(target_user.id)

        mock_user_repo = MagicMock()
        mock_user_repo.find_by_id.return_value = target_user
        mock_prefs_repo = MagicMock()
        mock_prefs_repo.disable_all.return_value = None

        with (
            patch(
                "backend.api.routes.notifications._get_user_repository",
                return_value=mock_user_repo,
            ),
            patch(
                "backend.api.routes.notifications._get_preferences_repository",
                return_value=mock_prefs_repo,
            ),
        ):
            response = client.get(
                f"/api/unsubscribe?user_id={target_user.id}&token={token}",
            )

        assert response.status_code == 200

    def test_unsubscribe_returns_success_message(
        self,
        client: Any,
        target_user: User,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """GET returns JSON body with a success message and user_id."""
        monkeypatch.setenv("UNSUBSCRIBE_SECRET", _TEST_SECRET)
        assert target_user.id is not None
        token = _make_valid_token(target_user.id)

        mock_user_repo = MagicMock()
        mock_user_repo.find_by_id.return_value = target_user
        mock_prefs_repo = MagicMock()

        with (
            patch(
                "backend.api.routes.notifications._get_user_repository",
                return_value=mock_user_repo,
            ),
            patch(
                "backend.api.routes.notifications._get_preferences_repository",
                return_value=mock_prefs_repo,
            ),
        ):
            response = client.get(
                f"/api/unsubscribe?user_id={target_user.id}&token={token}",
            )

        data = response.get_json()
        assert "message" in data
        assert "user_id" in data
        assert data["user_id"] == target_user.id

    def test_unsubscribe_calls_disable_all_for_user(
        self,
        client: Any,
        target_user: User,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """GET calls disable_all on the preferences repository."""
        monkeypatch.setenv("UNSUBSCRIBE_SECRET", _TEST_SECRET)
        assert target_user.id is not None
        token = _make_valid_token(target_user.id)

        mock_user_repo = MagicMock()
        mock_user_repo.find_by_id.return_value = target_user
        mock_prefs_repo = MagicMock()

        with (
            patch(
                "backend.api.routes.notifications._get_user_repository",
                return_value=mock_user_repo,
            ),
            patch(
                "backend.api.routes.notifications._get_preferences_repository",
                return_value=mock_prefs_repo,
            ),
        ):
            client.get(
                f"/api/unsubscribe?user_id={target_user.id}&token={token}",
            )

        mock_prefs_repo.disable_all.assert_called_once_with(target_user.id)

    def test_unsubscribe_does_not_require_auth_header(
        self,
        client: Any,
        target_user: User,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """GET succeeds without an Authorization header (unauthenticated)."""
        monkeypatch.setenv("UNSUBSCRIBE_SECRET", _TEST_SECRET)
        assert target_user.id is not None
        token = _make_valid_token(target_user.id)

        mock_user_repo = MagicMock()
        mock_user_repo.find_by_id.return_value = target_user
        mock_prefs_repo = MagicMock()

        with (
            patch(
                "backend.api.routes.notifications._get_user_repository",
                return_value=mock_user_repo,
            ),
            patch(
                "backend.api.routes.notifications._get_preferences_repository",
                return_value=mock_prefs_repo,
            ),
        ):
            response = client.get(
                f"/api/unsubscribe?user_id={target_user.id}&token={token}",
            )

        assert response.status_code == 200

    def test_unsubscribe_missing_user_id_returns_400(
        self,
        client: Any,
        target_user: User,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """GET without user_id parameter returns 400."""
        monkeypatch.setenv("UNSUBSCRIBE_SECRET", _TEST_SECRET)
        assert target_user.id is not None
        token = _make_valid_token(target_user.id)

        response = client.get(f"/api/unsubscribe?token={token}")

        assert response.status_code == 400

    def test_unsubscribe_missing_token_returns_400(
        self,
        client: Any,
        target_user: User,
    ) -> None:
        """GET without token parameter returns 400."""
        assert target_user.id is not None

        response = client.get(f"/api/unsubscribe?user_id={target_user.id}")

        assert response.status_code == 400

    def test_unsubscribe_tampered_token_returns_400(
        self,
        client: Any,
        target_user: User,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """GET with a modified token returns 400."""
        monkeypatch.setenv("UNSUBSCRIBE_SECRET", _TEST_SECRET)
        assert target_user.id is not None

        response = client.get(
            f"/api/unsubscribe?user_id={target_user.id}"
            "&token=aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
            "aaaaaaaaaaaaaaaaaaaaaaaaa",
        )

        assert response.status_code == 400

    def test_unsubscribe_token_for_different_user_returns_400(
        self,
        client: Any,
        target_user: User,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """GET with a token generated for a different user_id returns 400."""
        monkeypatch.setenv("UNSUBSCRIBE_SECRET", _TEST_SECRET)
        assert target_user.id is not None
        token_for_other_user = _make_valid_token(target_user.id + 1)

        response = client.get(
            f"/api/unsubscribe?user_id={target_user.id}"
            f"&token={token_for_other_user}",
        )

        assert response.status_code == 400

    def test_unsubscribe_nonexistent_user_returns_400(
        self,
        client: Any,
        target_user: User,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """GET with valid token but unknown user_id returns 400."""
        monkeypatch.setenv("UNSUBSCRIBE_SECRET", _TEST_SECRET)
        assert target_user.id is not None
        token = _make_valid_token(target_user.id)

        mock_user_repo = MagicMock()
        mock_user_repo.find_by_id.return_value = None

        with patch(
            "backend.api.routes.notifications._get_user_repository",
            return_value=mock_user_repo,
        ):
            response = client.get(
                f"/api/unsubscribe?user_id={target_user.id}&token={token}",
            )

        assert response.status_code == 400
