"""Unit tests for PostRevisionRepository conversion methods."""

import datetime as dt
from datetime import datetime
from unittest.mock import Mock
from uuid import uuid4

import pytest

from backend.domain.aggregates.post_revision import PostRevision
from backend.domain.value_objects.commit_sha import CommitSHA
from backend.infrastructure.persistence.models import PostRevisionModel
from backend.infrastructure.persistence.post_revision_repository import (
    PostRevisionRepository,
)


@pytest.fixture
def mock_session() -> Mock:
    """Mock SQLModel session for testing."""
    return Mock()


@pytest.fixture
def sample_revision_aggregate() -> PostRevision:
    """Sample PostRevision domain aggregate for testing."""
    return PostRevision.create(
        post_id=1,
        commit_sha="a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0",
        author_id=2,
        commit_message="Initial commit",
        markdown_content="# Test Post\n\nThis is test content.",
        is_revert=False,
    )


@pytest.fixture
def sample_revision_model() -> PostRevisionModel:
    """Sample PostRevisionModel for testing."""
    return PostRevisionModel(id=uuid4(),
        post_id=1,
        commit_sha="a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0",
        author_id=1,
        commit_message="Initial commit",
        markdown_content="# Test Post\n\nThis is test content.",
        created_at=datetime.now(dt.UTC),
        updated_at=datetime.now(dt.UTC),
        is_revert=False,
        attempt_count=0,
    )


class TestToModel:
    """Test _to_model conversion from domain to infrastructure."""

    def test_converts_all_fields_correctly(
        self, mock_session: Mock, sample_revision_aggregate: PostRevision
    ) -> None:
        """Test that all fields are correctly converted to model."""
        repo = PostRevisionRepository(session=mock_session)

        model = repo._to_model(
            sample_revision_aggregate, post_id=1, author_id=1
        )

        assert model.id == sample_revision_aggregate.id
        assert model.post_id == 1
        assert model.commit_sha == sample_revision_aggregate.commit_sha.value
        assert model.author_id == 1
        assert model.commit_message == sample_revision_aggregate.commit_message
        assert (
            model.markdown_content == sample_revision_aggregate.markdown_content
        )
        assert model.created_at == sample_revision_aggregate.created_at
        assert model.updated_at == sample_revision_aggregate.updated_at
        assert model.is_revert == sample_revision_aggregate.is_revert

    def test_extracts_commit_sha_value_object(
        self, mock_session: Mock, sample_revision_aggregate: PostRevision
    ) -> None:
        """Test that CommitSHA value object is extracted to string."""
        repo = PostRevisionRepository(session=mock_session)

        model = repo._to_model(
            sample_revision_aggregate, post_id=1, author_id=1
        )

        assert isinstance(model.commit_sha, str)
        assert model.commit_sha == "a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0"

    def test_preserves_timestamps(
        self, mock_session: Mock, sample_revision_aggregate: PostRevision
    ) -> None:
        """Test that created_at and updated_at are preserved."""
        repo = PostRevisionRepository(session=mock_session)

        model = repo._to_model(
            sample_revision_aggregate, post_id=1, author_id=1
        )

        assert model.created_at == sample_revision_aggregate.created_at
        assert model.updated_at == sample_revision_aggregate.updated_at


class TestToDomain:
    """Test _to_domain conversion from infrastructure to domain."""

    def test_converts_all_fields_correctly(
        self, mock_session: Mock, sample_revision_model: PostRevisionModel
    ) -> None:
        """Test that all fields are correctly converted to aggregate."""
        repo = PostRevisionRepository(session=mock_session)

        aggregate = repo._to_domain(
            sample_revision_model,
        )

        assert aggregate.id == sample_revision_model.id
        assert isinstance(aggregate.commit_sha, CommitSHA)
        assert aggregate.commit_sha.value == sample_revision_model.commit_sha
        assert aggregate.commit_message == sample_revision_model.commit_message
        assert (
            aggregate.markdown_content == sample_revision_model.markdown_content
        )
        assert aggregate.is_revert == sample_revision_model.is_revert

    def test_creates_commit_sha_value_object(
        self, mock_session: Mock, sample_revision_model: PostRevisionModel
    ) -> None:
        """Test string commit_sha converted to CommitSHA value object."""
        repo = PostRevisionRepository(session=mock_session)

        aggregate = repo._to_domain(
            sample_revision_model,
        )

        assert isinstance(aggregate.commit_sha, CommitSHA)
        assert (
            aggregate.commit_sha.value
            == "a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0"
        )

    def test_ensures_timezone_aware_datetimes(self, mock_session: Mock) -> None:
        """Test that naive datetimes are converted to UTC-aware."""
        naive_dt = datetime(2024, 1, 1, 12, 0, 0)
        model = PostRevisionModel(id=uuid4(),
            post_id=1,
            commit_sha="a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0",
            author_id=1,
            commit_message="Test",
            markdown_content="# Test",
            created_at=naive_dt,
            updated_at=naive_dt,
            is_revert=False,
            attempt_count=0,
        )

        repo = PostRevisionRepository(session=mock_session)
        aggregate = repo._to_domain(sample_revision_model)

        assert aggregate.created_at.tzinfo is not None
        assert aggregate.updated_at.tzinfo is not None
        assert aggregate.created_at.tzinfo == dt.UTC
        assert aggregate.updated_at.tzinfo == dt.UTC

    def test_preserves_utc_aware_datetimes(
        self, mock_session: Mock, sample_revision_model: PostRevisionModel
    ) -> None:
        """Test that UTC-aware datetimes are preserved."""
        utc_dt = datetime.now(dt.UTC)
        sample_revision_model.created_at = utc_dt
        sample_revision_model.updated_at = utc_dt

        repo = PostRevisionRepository(session=mock_session)
        aggregate = repo._to_domain(
            sample_revision_model,
        )

        assert aggregate.created_at == utc_dt
        assert aggregate.updated_at == utc_dt
        assert aggregate.created_at.tzinfo == dt.UTC
