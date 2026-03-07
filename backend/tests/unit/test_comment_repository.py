"""Unit tests for CommentRepository infrastructure layer.

This module tests the conversion between CommentModel (database) and Comment
aggregate (domain) to ensure proper field mapping and timezone awareness.

Test Coverage:
- _to_model field mapping: all fields, root comments, reply comments (3 tests)
- _to_domain field mapping: all fields, datetimes, flags, parent_id (7 tests)
"""

from datetime import UTC, datetime
from unittest.mock import Mock

import pytest

from backend.domain.aggregates.comment import Comment
from backend.domain.value_objects.comment_text import CommentText
from backend.infrastructure.persistence.comment_repository import (
    CommentRepository,
)
from backend.infrastructure.persistence.models import CommentModel


@pytest.fixture
def mock_session() -> Mock:
    """Fixture providing mock database session."""
    return Mock()


@pytest.fixture
def comment_domain_fixture() -> Comment:
    """Fixture providing a domain Comment aggregate created via factory."""
    return Comment.create(post_id=1, author_id=2, text="Hello world")


@pytest.fixture
def comment_model_fixture() -> CommentModel:
    """Fixture providing a CommentModel database table instance."""
    return CommentModel(
        id=10,
        post_id=1,
        author_id=2,
        text="Hello world",
        parent_id=None,
        created_at=datetime(2025, 6, 1, 10, 0, 0, tzinfo=UTC),
        updated_at=datetime(2025, 6, 1, 10, 0, 0, tzinfo=UTC),
        is_deleted=False,
        is_pending_moderation=False,
    )


def test_to_model_maps_all_fields(
    mock_session: Mock, comment_domain_fixture: Comment
) -> None:
    """Verify _to_model maps every Comment field to the CommentModel.

    All domain fields — post_id, author_id, text, parent_id, is_deleted,
    and is_pending_moderation — must appear on the returned model with
    matching values. text is the string form of the CommentText value object.
    """
    repo = CommentRepository(session=mock_session)
    model = repo._to_model(comment_domain_fixture)

    assert model.post_id == comment_domain_fixture.post_id
    assert model.author_id == comment_domain_fixture.author_id
    assert model.text == str(comment_domain_fixture.text)
    assert model.parent_id == comment_domain_fixture.parent_id
    assert model.is_deleted == comment_domain_fixture.is_deleted
    assert (
        model.is_pending_moderation
        == comment_domain_fixture.is_pending_moderation
    )


def test_to_model_with_none_parent_id(
    mock_session: Mock, comment_domain_fixture: Comment
) -> None:
    """Verify _to_model preserves None parent_id for root-level comments.

    A Comment created without a parent_id represents a top-level comment.
    The model field must remain None rather than being coerced to another value.
    """
    repo = CommentRepository(session=mock_session)
    model = repo._to_model(comment_domain_fixture)

    assert model.parent_id is None


def test_to_model_with_parent_id(mock_session: Mock) -> None:
    """Verify _to_model maps a non-None parent_id for reply comments.

    When a Comment is created with parent_id set, the resulting CommentModel
    must carry the same integer value to preserve the thread relationship.
    """
    reply = Comment.create(post_id=1, author_id=2, text="A reply", parent_id=5)
    repo = CommentRepository(session=mock_session)
    model = repo._to_model(reply)

    assert model.parent_id == 5


def test_to_domain_maps_all_fields(
    mock_session: Mock, comment_model_fixture: CommentModel
) -> None:
    """Verify _to_domain maps every CommentModel field to the Comment aggregate.

    All database fields should round-trip with correct types: text as a
    CommentText value object, ids as integers, and booleans preserved.
    """
    repo = CommentRepository(session=mock_session)
    domain = repo._to_domain(comment_model_fixture)

    assert domain.id == comment_model_fixture.id
    assert domain.post_id == comment_model_fixture.post_id
    assert domain.author_id == comment_model_fixture.author_id
    assert isinstance(domain.text, CommentText)
    assert str(domain.text) == comment_model_fixture.text
    assert domain.parent_id == comment_model_fixture.parent_id
    assert domain.is_deleted == comment_model_fixture.is_deleted
    assert (
        domain.is_pending_moderation
        == comment_model_fixture.is_pending_moderation
    )


def test_to_domain_handles_naive_datetime(mock_session: Mock) -> None:
    """Verify _to_domain adds UTC timezone to a naive created_at datetime.

    MySQL and some SQLite drivers return naive datetimes without tzinfo. The
    repository must attach UTC so that all domain datetimes are timezone-aware.
    """
    naive_created_at = datetime(2025, 6, 1, 10, 0, 0)
    model = CommentModel(
        id=1,
        post_id=1,
        author_id=2,
        text="Hello world",
        parent_id=None,
        created_at=naive_created_at,
        updated_at=datetime(2025, 6, 1, 10, 0, 0, tzinfo=UTC),
        is_deleted=False,
        is_pending_moderation=False,
    )

    repo = CommentRepository(session=mock_session)
    domain = repo._to_domain(model)

    assert domain.created_at.tzinfo is not None
    assert domain.created_at.tzinfo == UTC
    assert domain.created_at == naive_created_at.replace(tzinfo=UTC)


def test_to_domain_preserves_timezone_aware_datetime(
    mock_session: Mock,
) -> None:
    """Verify _to_domain preserves a timezone-aware created_at datetime.

    When the database model already carries a UTC-aware datetime, the
    repository must not alter it — value should be identical after conversion.
    """
    aware_created_at = datetime(2025, 6, 1, 10, 0, 0, tzinfo=UTC)
    model = CommentModel(
        id=1,
        post_id=1,
        author_id=2,
        text="Hello world",
        parent_id=None,
        created_at=aware_created_at,
        updated_at=datetime(2025, 6, 1, 10, 0, 0, tzinfo=UTC),
        is_deleted=False,
        is_pending_moderation=False,
    )

    repo = CommentRepository(session=mock_session)
    domain = repo._to_domain(model)

    assert domain.created_at == aware_created_at
    assert domain.created_at.tzinfo == UTC


def test_to_domain_with_none_parent_id(
    mock_session: Mock, comment_model_fixture: CommentModel
) -> None:
    """Verify _to_domain preserves None parent_id for root-level comment models.

    A CommentModel with parent_id=None represents a top-level comment.
    The resulting domain object must also have parent_id as None.
    """
    repo = CommentRepository(session=mock_session)
    domain = repo._to_domain(comment_model_fixture)

    assert domain.parent_id is None


def test_to_domain_with_parent_id(mock_session: Mock) -> None:
    """Verify _to_domain maps a non-None parent_id to the domain aggregate.

    When a CommentModel has a parent_id referencing another comment, the
    domain aggregate must carry the same integer value after conversion.
    """
    model = CommentModel(
        id=20,
        post_id=1,
        author_id=2,
        text="A reply",
        parent_id=5,
        created_at=datetime(2025, 6, 1, 10, 0, 0, tzinfo=UTC),
        updated_at=datetime(2025, 6, 1, 10, 0, 0, tzinfo=UTC),
        is_deleted=False,
        is_pending_moderation=False,
    )

    repo = CommentRepository(session=mock_session)
    domain = repo._to_domain(model)

    assert domain.parent_id == 5


def test_to_domain_deleted_comment(mock_session: Mock) -> None:
    """Verify _to_domain preserves is_deleted=True from a soft-deleted model.

    Soft-deleted comments must retain their deletion state when converted to
    domain aggregates so that moderation and display logic works correctly.
    """
    model = CommentModel(
        id=30,
        post_id=1,
        author_id=2,
        text="Deleted content",
        parent_id=None,
        created_at=datetime(2025, 6, 1, 10, 0, 0, tzinfo=UTC),
        updated_at=datetime(2025, 6, 1, 10, 0, 0, tzinfo=UTC),
        is_deleted=True,
        is_pending_moderation=False,
    )

    repo = CommentRepository(session=mock_session)
    domain = repo._to_domain(model)

    assert domain.is_deleted is True


def test_to_domain_pending_moderation_comment(mock_session: Mock) -> None:
    """Verify _to_domain preserves is_pending_moderation=True from the model.

    Comments flagged for review must retain that state in the domain aggregate
    so that moderation queues and visibility rules operate on accurate data.
    """
    model = CommentModel(
        id=40,
        post_id=1,
        author_id=2,
        text="Suspicious content",
        parent_id=None,
        created_at=datetime(2025, 6, 1, 10, 0, 0, tzinfo=UTC),
        updated_at=datetime(2025, 6, 1, 10, 0, 0, tzinfo=UTC),
        is_deleted=False,
        is_pending_moderation=True,
    )

    repo = CommentRepository(session=mock_session)
    domain = repo._to_domain(model)

    assert domain.is_pending_moderation is True
