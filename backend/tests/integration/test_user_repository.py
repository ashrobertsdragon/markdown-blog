"""Integration tests for UserRepository with real SQLite database.

This module defines comprehensive integration tests for the UserRepository
following TDD Red phase principles. These tests use an in-memory SQLite
database to test real database interactions.

Test Coverage:
- CRUD roundtrips: 6 tests (save+find_by_clerk_id, save+find_by_id, update,
  list_all, pagination, duplicate constraint)
- Edge cases: 3 tests (special characters, role conversion, timestamps)

Total: 9 integration tests
"""

import datetime as dt
from datetime import datetime

import pytest
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, SQLModel, create_engine

from backend.domain.aggregates.user import User as DomainUser
from backend.domain.value_objects.role import Role


@pytest.fixture
def db_session(test_settings):
    """Provide a database session for tests with in-memory SQLite."""
    engine = create_engine("sqlite:///:memory:", echo=False)

    SQLModel.metadata.create_all(engine)

    with Session(engine) as session:
        yield session
        session.rollback()

    SQLModel.metadata.drop_all(engine)
    engine.dispose()


def test_save_and_find_by_clerk_id_roundtrip(db_session):
    """Verify saving a user and retrieving by clerk_user_id works.

    This test ensures that a user can be saved to the database and
    retrieved by clerk_user_id with all fields intact, testing the
    full save-to-retrieve cycle.
    """
    from backend.infrastructure.persistence.user_repository import (
        UserRepository,
    )

    repo = UserRepository(db_session)

    new_user = DomainUser.create_from_clerk(
        clerk_user_id="user_clerk123", email="test@example.com"
    )

    saved_user = repo.save(new_user)
    assert saved_user.id is not None

    retrieved_user = repo.find_by_clerk_id("user_clerk123")

    assert retrieved_user is not None
    assert retrieved_user.id == saved_user.id
    assert retrieved_user.clerk_user_id == "user_clerk123"
    assert retrieved_user.email == "test@example.com"
    assert retrieved_user.role == Role.AUTHENTICATED


def test_save_and_find_by_id_roundtrip(db_session):
    """Verify saving a user and retrieving by ID works.

    This test ensures that a user can be saved to the database and
    retrieved by its database ID with all fields intact, testing the
    primary key lookup path.
    """
    from backend.infrastructure.persistence.user_repository import (
        UserRepository,
    )

    repo = UserRepository(db_session)

    new_user = DomainUser.create_from_clerk(
        clerk_user_id="user_id123", email="findbyid@example.com"
    )

    saved_user = repo.save(new_user)
    user_id = saved_user.id

    assert user_id is not None

    retrieved_user = repo.find_by_id(user_id)

    assert retrieved_user is not None
    assert retrieved_user.id == user_id
    assert retrieved_user.clerk_user_id == "user_id123"
    assert retrieved_user.email == "findbyid@example.com"


def test_save_update_persists_changes(db_session):
    """Verify updating an existing user persists changes to database.

    This test ensures that modifications to an existing user are
    properly saved and can be retrieved with the updated values,
    testing the UPDATE path of the repository.
    """
    from backend.infrastructure.persistence.user_repository import (
        UserRepository,
    )

    repo = UserRepository(db_session)

    new_user = DomainUser.create_from_clerk(
        clerk_user_id="user_update123", email="before@example.com"
    )
    saved_user = repo.save(new_user)

    saved_user.email = "after@example.com"
    saved_user.change_role(Role.AUTHOR)

    updated_user = repo.save(saved_user)

    retrieved_user = repo.find_by_id(updated_user.id)

    assert retrieved_user is not None
    assert retrieved_user.email == "after@example.com"
    assert retrieved_user.role == Role.AUTHOR


def test_list_all_returns_all_users(db_session):
    """Verify list_all returns all users from database.

    This test ensures that the list_all method correctly retrieves
    all users from the database, testing bulk retrieval functionality.
    """
    from backend.infrastructure.persistence.user_repository import (
        UserRepository,
    )

    repo = UserRepository(db_session)

    user1 = DomainUser.create_from_clerk(
        clerk_user_id="user_list1", email="user1@example.com"
    )
    user2 = DomainUser.create_from_clerk(
        clerk_user_id="user_list2", email="user2@example.com"
    )
    user3 = DomainUser.create_from_clerk(
        clerk_user_id="user_list3", email="user3@example.com"
    )

    repo.save(user1)
    repo.save(user2)
    repo.save(user3)

    all_users = repo.list_all()

    assert len(all_users) == 3
    clerk_ids = {user.clerk_user_id for user in all_users}
    assert clerk_ids == {"user_list1", "user_list2", "user_list3"}


def test_list_all_pagination_works(db_session):
    """Verify list_all pagination with limit and offset.

    This test ensures that pagination parameters correctly limit
    and offset results, testing that the SQL LIMIT/OFFSET clauses
    work as expected in the repository.
    """
    from backend.infrastructure.persistence.user_repository import (
        UserRepository,
    )

    repo = UserRepository(db_session)

    for i in range(10):
        user = DomainUser.create_from_clerk(
            clerk_user_id=f"user_page{i}", email=f"user{i}@example.com"
        )
        repo.save(user)

    page1 = repo.list_all(limit=3, offset=0)
    page2 = repo.list_all(limit=3, offset=3)

    assert len(page1) == 3
    assert len(page2) == 3

    page1_ids = {user.clerk_user_id for user in page1}
    page2_ids = {user.clerk_user_id for user in page2}

    assert len(page1_ids.intersection(page2_ids)) == 0


def test_duplicate_clerk_user_id_raises_integrity_error(db_session):
    """Verify duplicate clerk_user_id raises IntegrityError.

    This test ensures that the database unique constraint on
    clerk_user_id is enforced, preventing duplicate users from
    the same Clerk authentication.
    """
    from backend.infrastructure.persistence.user_repository import (
        UserRepository,
    )

    repo = UserRepository(db_session)

    user1 = DomainUser.create_from_clerk(
        clerk_user_id="user_duplicate", email="user1@example.com"
    )
    repo.save(user1)

    user2 = DomainUser.create_from_clerk(
        clerk_user_id="user_duplicate", email="user2@example.com"
    )

    with pytest.raises(IntegrityError):
        repo.save(user2)


def test_special_characters_in_clerk_id_handled_correctly(db_session):
    """Verify clerk_user_id with special characters is handled correctly.

    This test ensures that the repository properly handles clerk_user_id
    values containing special characters without SQL injection or
    database errors, testing parameterized query safety.
    """
    from backend.infrastructure.persistence.user_repository import (
        UserRepository,
    )

    repo = UserRepository(db_session)

    special_clerk_id = "user_2NJx@Gb#PQ$123"

    new_user = DomainUser.create_from_clerk(
        clerk_user_id=special_clerk_id, email="special@example.com"
    )

    repo.save(new_user)

    retrieved_user = repo.find_by_clerk_id(special_clerk_id)

    assert retrieved_user is not None
    assert retrieved_user.clerk_user_id == special_clerk_id


def test_role_enum_string_conversion_roundtrip(db_session):
    """Verify role enum-to-string-to-enum conversion works correctly.

    This test ensures that Role enums are correctly converted to
    strings for database storage and back to enums when retrieved,
    testing the full role conversion cycle for all role types.
    """
    from backend.infrastructure.persistence.user_repository import (
        UserRepository,
    )

    repo = UserRepository(db_session)

    roles = [Role.AUTHENTICATED, Role.AUTHOR, Role.ADMIN]

    for i, role in enumerate(roles):
        user = DomainUser(
            id=None,
            clerk_user_id=f"user_role{i}",
            email=f"role{i}@example.com",
            role=role,
            created_at=datetime.now(dt.UTC),
        )

        saved_user = repo.save(user)
        retrieved_user = repo.find_by_id(saved_user.id)

        assert retrieved_user is not None
        assert retrieved_user.role == role
        assert isinstance(retrieved_user.role, Role)


def test_created_at_timestamp_preserved_on_update(db_session):
    """Verify created_at timestamp is not modified on updates.

    This test ensures audit trail integrity: when updating an existing
    user, the created_at timestamp must remain unchanged, preserving
    the original creation time in the database.
    """
    from backend.infrastructure.persistence.user_repository import (
        UserRepository,
    )

    repo = UserRepository(db_session)

    original_timestamp = datetime(2024, 1, 15, 10, 30, 0, tzinfo=dt.UTC)

    new_user = DomainUser(
        id=None,
        clerk_user_id="user_timestamp",
        email="timestamp@example.com",
        role=Role.AUTHENTICATED,
        created_at=original_timestamp,
    )

    saved_user = repo.save(new_user)
    assert saved_user.created_at == original_timestamp

    saved_user.email = "updated@example.com"
    updated_user = repo.save(saved_user)

    retrieved_user = repo.find_by_id(updated_user.id)

    assert retrieved_user is not None
    assert retrieved_user.created_at == original_timestamp
