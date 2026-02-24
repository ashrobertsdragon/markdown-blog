"""Unit tests for PostRevision aggregate."""

from datetime import UTC, datetime, timedelta
from uuid import UUID

import pytest

from backend.domain.aggregates.post_revision import PostRevision
from backend.domain.value_objects.commit_sha import CommitSHA


class TestPostRevisionFactoryMethod:
    """Tests for PostRevision.create() factory method."""

    def test_post_revision_create_sets_all_fields(self) -> None:
        """Verify all required fields are set correctly."""
        post_id = 1
        author_id = 2
        commit_sha_str = "a" * 40
        commit_message = "Initial draft"
        markdown_content = "# Hello World"

        revision = PostRevision.create(
            post_id=post_id,
            commit_sha=commit_sha_str,
            author_id=author_id,
            commit_message=commit_message,
            markdown_content=markdown_content,
            is_revert=False,
        )

        assert revision.post_id == post_id
        assert revision.author_id == author_id
        assert str(revision.commit_sha) == commit_sha_str
        assert revision.commit_message == commit_message
        assert revision.markdown_content == markdown_content
        assert revision.is_revert is False

    def test_post_revision_create_has_timestamps(self) -> None:
        """Verify created_at and updated_at are UTC and recent."""
        post_id = 1
        author_id = 2
        commit_sha_str = "b" * 40
        before_creation = datetime.now(UTC)

        revision = PostRevision.create(
            post_id=post_id,
            commit_sha=commit_sha_str,
            author_id=author_id,
            commit_message="Test commit",
            markdown_content="Test content",
        )

        after_creation = datetime.now(UTC)

        assert revision.created_at.tzinfo == UTC
        assert revision.updated_at.tzinfo == UTC
        assert before_creation <= revision.created_at <= after_creation
        assert before_creation <= revision.updated_at <= after_creation
        assert revision.created_at == revision.updated_at

    def test_post_revision_create_generates_uuid_id(self) -> None:
        """Verify id is a valid UUID and not None."""
        post_id = 1
        author_id = 2
        commit_sha_str = "c" * 40

        revision = PostRevision.create(
            post_id=post_id,
            commit_sha=commit_sha_str,
            author_id=author_id,
            commit_message="Test commit",
            markdown_content="Test content",
        )

        assert revision.id is not None
        assert isinstance(revision.id, UUID)

    def test_post_revision_create_stores_commit_sha_object(self) -> None:
        """Verify commit_sha field stores CommitSHA object."""
        post_id = 1
        author_id = 2
        commit_sha_str = "d" * 40

        revision = PostRevision.create(
            post_id=post_id,
            commit_sha=commit_sha_str,
            author_id=author_id,
            commit_message="Test commit",
            markdown_content="Test content",
        )

        assert isinstance(revision.commit_sha, CommitSHA)


class TestPostRevisionFieldValidation:
    """Tests for PostRevision field validation."""

    def test_post_revision_create_rejects_none_post_id(self) -> None:
        """Raise ValueError if post_id is None."""
        commit_sha_str = "e" * 40
        author_id = 2

        with pytest.raises(ValueError, match="post_id cannot be None"):
            PostRevision.create(
                post_id=None,  # type: ignore[arg-type]
                commit_sha=commit_sha_str,
                author_id=author_id,
                commit_message="Test",
                markdown_content="Content",
            )

    def test_post_revision_create_rejects_invalid_post_id_type(self) -> None:
        """Raise TypeError if post_id is not int."""
        commit_sha_str = "f" * 40
        author_id = 2

        with pytest.raises(TypeError, match="post_id must be an int"):
            PostRevision.create(
                post_id="not-a-uuid",  # type: ignore
                commit_sha=commit_sha_str,
                author_id=author_id,
                commit_message="Test",
                markdown_content="Content",
            )

    def test_post_revision_create_rejects_none_author_id(self) -> None:
        """Raise ValueError if author_id is None."""
        commit_sha_str = "0" * 40
        post_id = 1

        with pytest.raises(ValueError, match="author_id cannot be None"):
            PostRevision.create(
                post_id=post_id,
                commit_sha=commit_sha_str,
                author_id=None,  # type: ignore
                commit_message="Test",
                markdown_content="Content",
            )

    def test_post_revision_create_rejects_invalid_author_id_type(self) -> None:
        """Raise TypeError if author_id is not int."""
        commit_sha_str = "1" * 40
        post_id = 1

        with pytest.raises(TypeError, match="author_id must be an int"):
            PostRevision.create(
                post_id=post_id,
                commit_sha=commit_sha_str,
                author_id="not-an-int",  # type: ignore
                commit_message="Test",
                markdown_content="Content",
            )

    def test_post_revision_create_rejects_empty_commit_message(self) -> None:
        """Raise ValueError if commit_message is empty string."""
        commit_sha_str = "2" * 40
        post_id = 1
        author_id = 2

        with pytest.raises(ValueError, match="commit_message cannot be empty"):
            PostRevision.create(
                post_id=post_id,
                commit_sha=commit_sha_str,
                author_id=author_id,
                commit_message="",
                markdown_content="Content",
            )

    def test_post_revision_create_rejects_none_commit_message(self) -> None:
        """Raise TypeError if commit_message is None."""
        commit_sha_str = "3" * 40
        post_id = 1
        author_id = 2

        with pytest.raises(TypeError, match="commit_message must be a string"):
            PostRevision.create(
                post_id=post_id,
                commit_sha=commit_sha_str,
                author_id=author_id,
                commit_message=None,  # type: ignore
                markdown_content="Content",
            )

    def test_post_revision_create_allows_empty_markdown_content(self) -> None:
        """Empty markdown_content is allowed."""
        commit_sha_str = "4" * 40
        post_id = 1
        author_id = 2

        revision = PostRevision.create(
            post_id=post_id,
            commit_sha=commit_sha_str,
            author_id=author_id,
            commit_message="Empty draft",
            markdown_content="",
        )

        assert revision.markdown_content == ""

    def test_post_revision_create_rejects_none_markdown_content(self) -> None:
        """Raise TypeError if markdown_content is None."""
        commit_sha_str = "5" * 40
        post_id = 1
        author_id = 2

        with pytest.raises(
            TypeError, match="markdown_content must be a string"
        ):
            PostRevision.create(
                post_id=post_id,
                commit_sha=commit_sha_str,
                author_id=author_id,
                commit_message="Test",
                markdown_content=None,  # type: ignore
            )

    def test_post_revision_create_invalid_commit_sha_propagates(self) -> None:
        """CommitSHA validation errors propagate to PostRevision.create()."""
        post_id = 1
        author_id = 2

        with pytest.raises(ValueError):
            PostRevision.create(
                post_id=post_id,
                commit_sha="invalid",
                author_id=author_id,
                commit_message="Test",
                markdown_content="Content",
            )


class TestPostRevisionImmutability:
    """Tests for PostRevision immutability."""

    def test_post_revision_is_immutable(self) -> None:
        """Cannot modify fields after creation."""
        commit_sha_str = "6" * 40
        post_id = 1
        author_id = 2

        revision = PostRevision.create(
            post_id=post_id,
            commit_sha=commit_sha_str,
            author_id=author_id,
            commit_message="Original message",
            markdown_content="Original content",
        )

        with pytest.raises(Exception):
            revision.commit_message = "Modified message"  # type: ignore

        with pytest.raises(Exception):
            revision.markdown_content = "Modified content"  # type: ignore

    def test_post_revision_prevents_timestamp_modification(self) -> None:
        """Timestamps cannot be changed."""
        commit_sha_str = "7" * 40
        post_id = 1
        author_id = 2

        revision = PostRevision.create(
            post_id=post_id,
            commit_sha=commit_sha_str,
            author_id=author_id,
            commit_message="Test",
            markdown_content="Content",
        )

        original_created_at = revision.created_at
        new_timestamp = datetime.now(UTC) + timedelta(hours=1)

        with pytest.raises(Exception):
            revision.created_at = new_timestamp  # type: ignore

        assert revision.created_at == original_created_at

    def test_post_revision_commit_sha_value_immutable(self) -> None:
        """CommitSHA object is immutable."""
        commit_sha_str = "8" * 40
        post_id = 1
        author_id = 2

        revision = PostRevision.create(
            post_id=post_id,
            commit_sha=commit_sha_str,
            author_id=author_id,
            commit_message="Test",
            markdown_content="Content",
        )

        with pytest.raises(Exception):
            revision.commit_sha = CommitSHA("9" * 40)  # type: ignore


class TestPostRevisionProperties:
    """Tests for PostRevision property methods."""

    def test_post_revision_get_markdown_content_returns_string(self) -> None:
        """Property retrieves markdown content."""
        commit_sha_str = "a" * 40
        post_id = 1
        author_id = 2
        markdown_content = "# Test Content\n\nThis is a test."

        revision = PostRevision.create(
            post_id=post_id,
            commit_sha=commit_sha_str,
            author_id=author_id,
            commit_message="Test",
            markdown_content=markdown_content,
        )

        assert revision.get_markdown_content() == markdown_content
        assert isinstance(revision.get_markdown_content(), str)

    def test_post_revision_get_commit_message_returns_string(self) -> None:
        """Property retrieves commit message."""
        commit_sha_str = "b" * 40
        post_id = 1
        author_id = 2
        commit_message = "Initial commit with detailed message"

        revision = PostRevision.create(
            post_id=post_id,
            commit_sha=commit_sha_str,
            author_id=author_id,
            commit_message=commit_message,
            markdown_content="Content",
        )

        assert revision.get_commit_message() == commit_message
        assert isinstance(revision.get_commit_message(), str)
