"""Unit tests for UserRepository.find_by_email_prefix().

Covers:
- Returns a DomainUser when a user with a matching email prefix exists
- Returns None when no user matches the given email prefix
"""

from datetime import UTC, datetime
from unittest.mock import MagicMock

from backend.domain.aggregates.user import User as DomainUser
from backend.domain.value_objects.role import Role
from backend.infrastructure.persistence.models import User as UserModel
from backend.infrastructure.persistence.user_repository import UserRepository


def _make_user_model(
    user_id: int = 1,
    email: str = "alice@example.com",
    clerk_user_id: str = "clerk_001",
    role: str = "authenticated",
) -> UserModel:
    """Build a minimal UserModel for test use."""
    return UserModel(
        id=user_id,
        email=email,
        clerk_user_id=clerk_user_id,
        role=role,
        created_at=datetime(2024, 1, 1, tzinfo=UTC),
    )


class TestFindByEmailPrefix:
    """Tests for UserRepository.find_by_email_prefix()."""

    def test_returns_domain_user_when_prefix_matches(self) -> None:
        """Returns a DomainUser when the email prefix matches a stored user."""
        user_model = _make_user_model(user_id=7, email="alice@example.com")
        mock_session = MagicMock()
        mock_session.exec.return_value.first.return_value = user_model

        repo = UserRepository(session=mock_session)
        result = repo.find_by_email_prefix("alice")

        assert isinstance(result, DomainUser)
        assert result.id == 7
        assert result.email == "alice@example.com"

    def test_returns_none_when_no_match(self) -> None:
        """Returns None when no user has an email with the given prefix."""
        mock_session = MagicMock()
        mock_session.exec.return_value.first.return_value = None

        repo = UserRepository(session=mock_session)
        result = repo.find_by_email_prefix("nobody")

        assert result is None

    def test_returned_user_has_correct_role(self) -> None:
        """DomainUser returned from prefix lookup carries the correct role."""
        user_model = _make_user_model(email="bob@example.com", role="admin")
        mock_session = MagicMock()
        mock_session.exec.return_value.first.return_value = user_model

        repo = UserRepository(session=mock_session)
        result = repo.find_by_email_prefix("bob")

        assert result is not None
        assert result.role == Role("admin")
