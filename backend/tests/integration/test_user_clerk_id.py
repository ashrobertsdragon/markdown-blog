"""Integration tests for User.clerk_user_id database constraints."""

import pytest
from sqlalchemy import inspect
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session

from backend.infrastructure.persistence.database import get_engine
from backend.infrastructure.persistence.models import User


@pytest.fixture
def db_session():
    """Provide a database session for tests."""
    engine = get_engine()
    with Session(engine) as session:
        yield session
        session.rollback()


def test_clerk_user_id_unique_constraint(db_session):
    """Database should prevent duplicate clerk_user_ids."""
    clerk_id = "clerk_test_user_12345"

    user1 = User(
        clerk_user_id=clerk_id, email="user1@example.com", role="reader"
    )
    db_session.add(user1)
    db_session.commit()

    user2 = User(
        clerk_user_id=clerk_id, email="user2@example.com", role="reader"
    )
    db_session.add(user2)

    with pytest.raises(IntegrityError) as exc_info:
        db_session.commit()

    assert "clerk_user_id" in str(exc_info.value).lower()


def test_clerk_user_id_allows_multiple_nulls(db_session):
    """Database should allow multiple users with NULL clerk_user_id."""
    user1 = User(email="user3@example.com", role="reader")
    user2 = User(email="user4@example.com", role="reader")

    db_session.add(user1)
    db_session.add(user2)
    db_session.commit()

    db_session.refresh(user1)
    db_session.refresh(user2)

    assert user1.clerk_user_id is None
    assert user2.clerk_user_id is None


def test_clerk_user_id_index_exists(db_session):
    """Database should have index on clerk_user_id for performance."""
    engine = get_engine()
    inspector = inspect(engine)

    indexes = inspector.get_indexes("user")

    clerk_id_indexed = False
    for index in indexes:
        if "clerk_user_id" in index["column_names"]:
            clerk_id_indexed = True
            break

    assert clerk_id_indexed, "clerk_user_id column should have an index"
