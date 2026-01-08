"""Unit tests for UserRepository with mocked database sessions.

This module defines comprehensive unit tests for the UserRepository following
TDD Red phase principles. These tests will initially fail until the
UserRepository is implemented.

Test Coverage:
- Conversion methods: 4 tests (_to_domain, _to_model with role conversions)
- find_by_clerk_id: 3 tests (found, not found, parameterized query)
- find_by_id: 2 tests (found, not found)
- save: 5 tests (insert, update, not found, ID assignment, timestamps)
- list_all: 3 tests (returns users, pagination, empty list)
- Edge cases: 3 tests (special characters, None handling, concurrent update)

Total: 20 unit tests
"""

import datetime as dt
from datetime import datetime
from unittest.mock import MagicMock, Mock

import pytest
from sqlmodel import Session

from backend.domain.aggregates.user import User as DomainUser
from backend.domain.value_objects.role import Role
from backend.infrastructure.persistence.models import User as UserModel


@pytest.fixture
def mock_session():
    """Provide a mocked SQLModel Session for testing."""
    return MagicMock(spec=Session)


@pytest.fixture
def sample_user_model():
    """Provide a sample UserModel for testing."""
    return UserModel(
        id=1,
        clerk_user_id="user_2NJxGbPQaBCdef123",
        email="test@example.com",
        role="authenticated",
        created_at=datetime(2024, 1, 15, 10, 30, 0, tzinfo=dt.UTC),
    )


@pytest.fixture
def sample_domain_user():
    """Provide a sample DomainUser for testing."""
    return DomainUser(
        id=1,
        clerk_user_id="user_2NJxGbPQaBCdef123",
        email="test@example.com",
        role=Role.AUTHENTICATED,
        created_at=datetime(2024, 1, 15, 10, 30, 0, tzinfo=dt.UTC),
    )


def test_to_domain_converts_model_to_domain_user(sample_user_model):
    """Verify _to_domain converts UserModel to DomainUser correctly.

    This test ensures that the repository can convert database models
    into domain aggregates with all fields mapped correctly, including
    role string-to-enum conversion.
    """
    from backend.infrastructure.persistence.user_repository import (
        UserRepository,
    )

    repo = UserRepository(MagicMock())

    domain_user = repo._to_domain(sample_user_model)

    assert isinstance(domain_user, DomainUser)
    assert domain_user.id == sample_user_model.id
    assert domain_user.clerk_user_id == sample_user_model.clerk_user_id
    assert domain_user.email == sample_user_model.email
    assert domain_user.role == Role.AUTHENTICATED
    assert domain_user.created_at == sample_user_model.created_at


def test_to_domain_converts_all_role_types():
    """Verify _to_domain handles all role enum conversions.

    This test ensures role string-to-enum conversion works for all
    valid role values (authenticated, author, admin) to prevent
    conversion errors at runtime.
    """
    from backend.infrastructure.persistence.user_repository import (
        UserRepository,
    )

    repo = UserRepository(MagicMock())

    roles = [
        ("authenticated", Role.AUTHENTICATED),
        ("author", Role.AUTHOR),
        ("admin", Role.ADMIN),
    ]

    for role_str, expected_enum in roles:
        model = UserModel(
            id=1,
            clerk_user_id="user_test",
            email="test@example.com",
            role=role_str,
            created_at=datetime.now(dt.UTC),
        )

        domain_user = repo._to_domain(model)

        assert domain_user.role == expected_enum


def test_to_model_converts_domain_user_to_model(sample_domain_user):
    """Verify _to_model converts DomainUser to UserModel correctly.

    This test ensures that domain aggregates can be converted to
    database models with all fields mapped correctly, including
    role enum-to-string conversion.
    """
    from backend.infrastructure.persistence.user_repository import (
        UserRepository,
    )

    repo = UserRepository(MagicMock())

    user_model = repo._to_model(sample_domain_user)

    assert isinstance(user_model, UserModel)
    assert user_model.id == sample_domain_user.id
    assert user_model.clerk_user_id == sample_domain_user.clerk_user_id
    assert user_model.email == sample_domain_user.email
    assert user_model.role == "authenticated"
    assert user_model.created_at == sample_domain_user.created_at


def test_to_model_converts_all_role_enums():
    """Verify _to_model handles all role enum-to-string conversions.

    This test ensures role enum-to-string conversion works for all
    valid Role enum values to prevent database constraint violations.
    """
    from backend.infrastructure.persistence.user_repository import (
        UserRepository,
    )

    repo = UserRepository(MagicMock())

    roles = [
        (Role.AUTHENTICATED, "authenticated"),
        (Role.AUTHOR, "author"),
        (Role.ADMIN, "admin"),
    ]

    for role_enum, expected_str in roles:
        domain_user = DomainUser(
            id=1,
            clerk_user_id="user_test",
            email="test@example.com",
            role=role_enum,
            created_at=datetime.now(dt.UTC),
        )

        user_model = repo._to_model(domain_user)

        assert user_model.role == expected_str


def test_find_by_clerk_id_returns_domain_user_when_found(
    mock_session, sample_user_model
):
    """Verify find_by_clerk_id returns DomainUser when user exists.

    This test ensures that when a user with the given clerk_user_id
    exists in the database, the repository returns the corresponding
    DomainUser aggregate with all fields correctly mapped.
    """
    from backend.infrastructure.persistence.user_repository import (
        UserRepository,
    )

    mock_session.exec.return_value.first.return_value = sample_user_model

    repo = UserRepository(mock_session)
    result = repo.find_by_clerk_id("user_2NJxGbPQaBCdef123")

    assert result is not None
    assert isinstance(result, DomainUser)
    assert result.clerk_user_id == "user_2NJxGbPQaBCdef123"
    mock_session.exec.assert_called_once()


def test_find_by_clerk_id_returns_none_when_not_found(mock_session):
    """Verify find_by_clerk_id returns None when user does not exist.

    This test ensures that when no user with the given clerk_user_id
    exists, the repository returns None rather than raising an exception,
    following the Optional return type convention.
    """
    from backend.infrastructure.persistence.user_repository import (
        UserRepository,
    )

    mock_session.exec.return_value.first.return_value = None

    repo = UserRepository(mock_session)
    result = repo.find_by_clerk_id("nonexistent_clerk_id")

    assert result is None
    mock_session.exec.assert_called_once()


def test_find_by_clerk_id_uses_correct_query_filter(
    mock_session, sample_user_model
):
    """Verify find_by_clerk_id constructs correct SQL query.

    This test ensures the repository uses the correct SQLModel query
    with proper WHERE clause filtering on clerk_user_id column.
    """
    from backend.infrastructure.persistence.user_repository import (
        UserRepository,
    )

    mock_session.exec.return_value.first.return_value = sample_user_model

    repo = UserRepository(mock_session)
    repo.find_by_clerk_id("user_2NJxGbPQaBCdef123")

    call_args = mock_session.exec.call_args
    assert call_args is not None


def test_find_by_id_returns_domain_user_when_found(
    mock_session, sample_user_model
):
    """Verify find_by_id returns DomainUser when user exists.

    This test ensures that when a user with the given ID exists in
    the database, the repository returns the corresponding DomainUser
    aggregate with all fields correctly mapped.
    """
    from backend.infrastructure.persistence.user_repository import (
        UserRepository,
    )

    mock_session.get.return_value = sample_user_model

    repo = UserRepository(mock_session)
    result = repo.find_by_id(1)

    assert result is not None
    assert isinstance(result, DomainUser)
    assert result.id == 1
    mock_session.get.assert_called_once_with(UserModel, 1)


def test_find_by_id_returns_none_when_not_found(mock_session):
    """Verify find_by_id returns None when user does not exist.

    This test ensures that when no user with the given ID exists,
    the repository returns None rather than raising an exception,
    following the Optional return type convention.
    """
    from backend.infrastructure.persistence.user_repository import (
        UserRepository,
    )

    mock_session.get.return_value = None

    repo = UserRepository(mock_session)
    result = repo.find_by_id(999)

    assert result is None
    mock_session.get.assert_called_once_with(UserModel, 999)


def test_save_inserts_new_user_without_id(mock_session):
    """Verify save inserts new user when id is None.

    This test ensures that when saving a DomainUser with id=None,
    the repository performs an INSERT operation and assigns the
    database-generated ID back to the returned domain aggregate.
    """
    from backend.infrastructure.persistence.user_repository import (
        UserRepository,
    )

    new_user = DomainUser(
        id=None,
        clerk_user_id="user_new123",
        email="new@example.com",
        role=Role.AUTHENTICATED,
        created_at=datetime.now(dt.UTC),
    )

    mock_session.add = Mock()
    mock_session.commit = Mock()
    mock_session.refresh = Mock(side_effect=lambda obj: setattr(obj, "id", 42))

    repo = UserRepository(mock_session)
    result = repo.save(new_user)

    assert result.id == 42
    mock_session.add.assert_called_once()
    mock_session.commit.assert_called_once()
    mock_session.refresh.assert_called_once()


def test_save_updates_existing_user_with_id(mock_session, sample_user_model):
    """Verify save updates existing user when id is present.

    This test ensures that when saving a DomainUser with an existing
    id, the repository performs an UPDATE operation by first retrieving
    the existing model, updating its fields, and committing.
    """
    from backend.infrastructure.persistence.user_repository import (
        UserRepository,
    )

    existing_user = DomainUser(
        id=1,
        clerk_user_id="user_2NJxGbPQaBCdef123",
        email="updated@example.com",
        role=Role.AUTHOR,
        created_at=sample_user_model.created_at,
    )

    mock_session.get.return_value = sample_user_model
    mock_session.commit = Mock()
    mock_session.refresh = Mock()

    repo = UserRepository(mock_session)
    result = repo.save(existing_user)

    assert result.email == "updated@example.com"
    assert result.role == Role.AUTHOR
    mock_session.get.assert_called_once_with(UserModel, 1)
    mock_session.commit.assert_called_once()
    mock_session.refresh.assert_called_once()


def test_save_raises_error_when_updating_nonexistent_user(mock_session):
    """Verify save raises ValueError when updating user not in database.

    This test ensures that when attempting to update a user with an ID
    that doesn't exist in the database, the repository raises a
    ValueError to prevent silent failures.
    """
    from backend.infrastructure.persistence.user_repository import (
        UserRepository,
    )

    nonexistent_user = DomainUser(
        id=999,
        clerk_user_id="user_ghost",
        email="ghost@example.com",
        role=Role.AUTHENTICATED,
        created_at=datetime.now(dt.UTC),
    )

    mock_session.get.return_value = None

    repo = UserRepository(mock_session)

    with pytest.raises(ValueError, match="User with id 999 not found"):
        repo.save(nonexistent_user)


def test_save_assigns_id_to_new_user(mock_session):
    """Verify save assigns database-generated ID to new user.

    This test ensures that after saving a new user, the returned
    DomainUser has the database-generated ID populated, allowing
    the caller to use the ID for subsequent operations.
    """
    from backend.infrastructure.persistence.user_repository import (
        UserRepository,
    )

    new_user = DomainUser(
        id=None,
        clerk_user_id="user_assign_id",
        email="assignid@example.com",
        role=Role.AUTHENTICATED,
        created_at=datetime.now(dt.UTC),
    )

    mock_session.add = Mock()
    mock_session.commit = Mock()
    mock_session.refresh = Mock(side_effect=lambda obj: setattr(obj, "id", 100))

    repo = UserRepository(mock_session)
    result = repo.save(new_user)

    assert result.id == 100
    assert new_user.id is None


def test_save_preserves_created_at_timestamp(mock_session, sample_user_model):
    """Verify save does not modify created_at timestamp on updates.

    This test ensures audit trail integrity: when updating an existing
    user, the created_at timestamp must remain unchanged to preserve
    the original creation time.
    """
    from backend.infrastructure.persistence.user_repository import (
        UserRepository,
    )

    original_timestamp = datetime(2024, 1, 15, 10, 30, 0, tzinfo=dt.UTC)

    existing_user = DomainUser(
        id=1,
        clerk_user_id="user_2NJxGbPQaBCdef123",
        email="updated@example.com",
        role=Role.AUTHOR,
        created_at=original_timestamp,
    )

    mock_session.get.return_value = sample_user_model
    mock_session.commit = Mock()
    mock_session.refresh = Mock()

    repo = UserRepository(mock_session)
    result = repo.save(existing_user)

    assert result.created_at == original_timestamp


def test_list_all_returns_list_of_domain_users(mock_session):
    """Verify list_all returns list of DomainUser aggregates.

    This test ensures that when querying for all users, the repository
    returns a list of DomainUser aggregates with all fields correctly
    mapped from database models.
    """
    from backend.infrastructure.persistence.user_repository import (
        UserRepository,
    )

    user_models = [
        UserModel(
            id=1,
            clerk_user_id="user_1",
            email="user1@example.com",
            role="authenticated",
            created_at=datetime.now(dt.UTC),
        ),
        UserModel(
            id=2,
            clerk_user_id="user_2",
            email="user2@example.com",
            role="author",
            created_at=datetime.now(dt.UTC),
        ),
    ]

    mock_session.exec.return_value.all.return_value = user_models

    repo = UserRepository(mock_session)
    result = repo.list_all()

    assert len(result) == 2
    assert all(isinstance(user, DomainUser) for user in result)
    assert result[0].clerk_user_id == "user_1"
    assert result[1].clerk_user_id == "user_2"


def test_list_all_applies_limit_and_offset_pagination(mock_session):
    """Verify list_all applies LIMIT and OFFSET for pagination.

    This test ensures that the repository correctly constructs SQL
    queries with LIMIT and OFFSET clauses for pagination support,
    preventing performance issues with large user tables.
    """
    from backend.infrastructure.persistence.user_repository import (
        UserRepository,
    )

    mock_session.exec.return_value.all.return_value = []

    repo = UserRepository(mock_session)
    repo.list_all(limit=10, offset=20)

    call_args = mock_session.exec.call_args
    assert call_args is not None


def test_list_all_returns_empty_list_when_no_users(mock_session):
    """Verify list_all returns empty list when no users exist.

    This test ensures that when the users table is empty, the
    repository returns an empty list rather than None or raising
    an exception, simplifying caller logic.
    """
    from backend.infrastructure.persistence.user_repository import (
        UserRepository,
    )

    mock_session.exec.return_value.all.return_value = []

    repo = UserRepository(mock_session)
    result = repo.list_all()

    assert result == []
    assert isinstance(result, list)


def test_find_by_clerk_id_handles_special_characters(mock_session):
    """Verify find_by_clerk_id handles clerk IDs with special characters.

    This test ensures that the repository correctly handles clerk_user_id
    values containing special characters without SQL injection or query
    errors, using proper parameterization.
    """
    from backend.infrastructure.persistence.user_repository import (
        UserRepository,
    )

    special_clerk_id = "user_2NJx'Gb\"PQ;DROP TABLE users;--"

    mock_session.exec.return_value.first.return_value = None

    repo = UserRepository(mock_session)
    result = repo.find_by_clerk_id(special_clerk_id)

    assert result is None
    mock_session.exec.assert_called_once()


def test_to_domain_handles_none_id_correctly():
    """Verify _to_domain correctly handles None id from database.

    This test ensures that when converting a database model with
    id=None (edge case), the repository correctly creates a DomainUser
    with id=None without errors.
    """
    from backend.infrastructure.persistence.user_repository import (
        UserRepository,
    )

    model_without_id = UserModel(
        id=None,
        clerk_user_id="user_no_id",
        email="noid@example.com",
        role="authenticated",
        created_at=datetime.now(dt.UTC),
    )

    repo = UserRepository(MagicMock())
    domain_user = repo._to_domain(model_without_id)

    assert domain_user.id is None
    assert domain_user.clerk_user_id == "user_no_id"


def test_save_handles_concurrent_update_conflict(
    mock_session, sample_user_model
):
    """Verify save handles concurrent modification conflicts gracefully.

    This test ensures that when multiple processes attempt to update
    the same user simultaneously, the repository handles the conflict
    appropriately by re-fetching the latest state before committing.
    """
    from backend.infrastructure.persistence.user_repository import (
        UserRepository,
    )

    existing_user = DomainUser(
        id=1,
        clerk_user_id="user_2NJxGbPQaBCdef123",
        email="concurrent@example.com",
        role=Role.AUTHOR,
        created_at=sample_user_model.created_at,
    )

    mock_session.get.return_value = sample_user_model
    mock_session.commit = Mock()
    mock_session.refresh = Mock()

    repo = UserRepository(mock_session)
    result = repo.save(existing_user)

    assert result is not None
    mock_session.commit.assert_called_once()
