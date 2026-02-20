"""Integration tests for CreateDraftHandler.

This module defines comprehensive integration tests for the CreateDraftHandler
following TDD Red phase principles. These tests will initially fail until the
handler is implemented.

Test Coverage:
- Happy path: successful draft creation (1 test)
- Uniqueness validation: database and filesystem (2 tests)
- Slug normalization (1 test)
- YAML front matter generation (1 test)
- Domain validation: empty title, invalid author_id, invalid slug (3 tests)
- GitHub resilience: continues on GitHub failure (1 test)
- Timestamp validation (1 test)

Total: 10 integration tests
"""

import datetime as dt
from datetime import datetime
from pathlib import Path
from unittest.mock import Mock

import pytest

from backend.application.commands.create_draft_command import (
    CreateDraftCommand,
)
from backend.application.commands.handlers.create_draft_handler import (
    create_draft_handler,
)
from backend.domain.aggregates.post import Post
from backend.infrastructure.persistence.filesystem_draft_repository import (
    DraftFile,
    FileSystemDraftRepository,
)
from backend.infrastructure.versioning.github_sync_service import (
    GitHubSyncService,
)


@pytest.fixture
def draft_repository(tmp_path: Path) -> FileSystemDraftRepository:
    """Fixture providing FileSystemDraftRepository with temp directory."""
    return FileSystemDraftRepository(tmp_path)


@pytest.fixture
def mock_post_repository() -> Mock:
    """Fixture providing mock PostRepository."""
    mock_repo = Mock()
    mock_repo.find_by_slug.return_value = None
    mock_repo.save.side_effect = lambda post: post
    return mock_repo


@pytest.fixture
def mock_github_service() -> Mock:
    """Fixture providing mock GitHubSyncService."""
    mock_service = Mock(spec=GitHubSyncService)
    mock_service.commit_file.return_value = "abc123def456"
    return mock_service


def test_handler_creates_draft_successfully(
    draft_repository: FileSystemDraftRepository,
    mock_post_repository: Mock,
    mock_github_service: Mock,
) -> None:
    """Verify handler orchestrates full draft creation workflow.

    This is the happy path test. The handler should:
    1. Check uniqueness (DB and filesystem)
    2. Create Post aggregate via create_draft()
    3. Save to filesystem with YAML front matter
    4. Commit to GitHub
    5. Save Post to database
    6. Return created Post

    All operations should succeed without errors.
    """
    command = CreateDraftCommand(
        slug="my-first-post", title="My First Post", author_id=1
    )

    result = create_draft_handler(
        command=command,
        draft_repo=draft_repository,
        post_repo=mock_post_repository,
        github_service=mock_github_service,
    )

    assert result is not None
    assert str(result.slug) == "my-first-post"
    assert result.title == "My First Post"
    assert result.author_id == 1
    assert result.published is False

    mock_post_repository.find_by_slug.assert_called_once_with("my-first-post")
    mock_post_repository.save.assert_called_once()
    mock_github_service.commit_file.assert_called_once()


def test_handler_raises_error_for_existing_database_slug(
    draft_repository: FileSystemDraftRepository,
    mock_post_repository: Mock,
    mock_github_service: Mock,
) -> None:
    """Verify handler rejects duplicate slug in database.

    This test ensures uniqueness validation at the database level. If a
    Post with the same slug already exists in the database, the handler
    should raise ValueError before attempting filesystem or GitHub
    operations.
    """
    existing_post = Post.create_draft("existing-post", "Existing Post", 1)
    mock_post_repository.find_by_slug.return_value = existing_post

    command = CreateDraftCommand(
        slug="existing-post", title="Duplicate Post", author_id=2
    )

    with pytest.raises(ValueError, match="already exists|duplicate"):
        create_draft_handler(
            command=command,
            draft_repo=draft_repository,
            post_repo=mock_post_repository,
            github_service=mock_github_service,
        )

    mock_post_repository.find_by_slug.assert_called_once_with("existing-post")
    mock_post_repository.save.assert_not_called()
    mock_github_service.commit_file.assert_not_called()


def test_handler_raises_error_for_existing_filesystem_slug(
    draft_repository: FileSystemDraftRepository,
    mock_post_repository: Mock,
    mock_github_service: Mock,
) -> None:
    """Verify handler rejects duplicate slug in filesystem.

    This test ensures uniqueness validation at the filesystem level. If a
    draft file with the same slug already exists in the filesystem, the
    handler should raise ValueError even if the database check passes.
    """
    existing_draft = DraftFile(
        slug="existing-draft",
        title="Existing Draft",
        author="alice",
        content="Existing content",
        published=False,
        created_at=datetime(2026, 1, 19, 12, 0, 0, tzinfo=dt.UTC),
    )
    draft_repository.save(existing_draft)

    command = CreateDraftCommand(
        slug="existing-draft", title="Duplicate Draft", author_id=1
    )

    with pytest.raises(ValueError, match="already exists|duplicate"):
        create_draft_handler(
            command=command,
            draft_repo=draft_repository,
            post_repo=mock_post_repository,
            github_service=mock_github_service,
        )

    mock_post_repository.save.assert_not_called()
    mock_github_service.commit_file.assert_not_called()


def test_handler_normalizes_slug(
    draft_repository: FileSystemDraftRepository,
    mock_post_repository: Mock,
    mock_github_service: Mock,
) -> None:
    """Verify handler normalizes slug via Slug value object.

    This test ensures slug normalization happens correctly. The handler
    should use the Slug value object which normalizes the input (lowercase,
    hyphens, special chars removed). The test verifies "My First Post!!"
    becomes "my-first-post".
    """
    command = CreateDraftCommand(
        slug="My First Post!!", title="My First Post", author_id=1
    )

    result = create_draft_handler(
        command=command,
        draft_repo=draft_repository,
        post_repo=mock_post_repository,
        github_service=mock_github_service,
    )

    assert result is not None
    assert str(result.slug) == "my-first-post"

    file_path = draft_repository.drafts_path / "my-first-post.md"
    assert file_path.exists()


def test_handler_creates_yaml_front_matter(
    draft_repository: FileSystemDraftRepository,
    mock_post_repository: Mock,
    mock_github_service: Mock,
) -> None:
    """Verify handler creates file with proper YAML front matter.

    This test ensures the draft file is created with correct YAML front
    matter structure. The file should have:
    - YAML delimiters (---)
    - title field
    - author field (from author_id lookup or placeholder)
    - published: false
    - created_at timestamp
    - Empty content section
    """
    command = CreateDraftCommand(
        slug="yaml-test", title="YAML Test Post", author_id=1
    )

    create_draft_handler(
        command=command,
        draft_repo=draft_repository,
        post_repo=mock_post_repository,
        github_service=mock_github_service,
    )

    file_path = draft_repository.drafts_path / "yaml-test.md"
    assert file_path.exists()

    content = file_path.read_text(encoding="utf-8")

    assert content.startswith("---\n")
    assert "title: YAML Test Post" in content
    assert "published: false" in content or "published: False" in content
    assert "created_at:" in content
    assert content.count("---") >= 2


def test_handler_raises_error_for_empty_title(
    draft_repository: FileSystemDraftRepository,
    mock_post_repository: Mock,
    mock_github_service: Mock,
) -> None:
    """Verify handler rejects empty title.

    This test ensures domain validation happens via Post aggregate.
    Empty or whitespace-only titles should raise ValueError from the
    Post.create_draft() method, preventing creation of invalid drafts.
    """
    command = CreateDraftCommand(slug="valid-slug", title="", author_id=1)

    with pytest.raises(ValueError, match="title"):
        create_draft_handler(
            command=command,
            draft_repo=draft_repository,
            post_repo=mock_post_repository,
            github_service=mock_github_service,
        )

    mock_post_repository.save.assert_not_called()
    mock_github_service.commit_file.assert_not_called()


def test_handler_raises_error_for_invalid_author_id(
    draft_repository: FileSystemDraftRepository,
    mock_post_repository: Mock,
    mock_github_service: Mock,
) -> None:
    """Verify handler rejects invalid author_id.

    This test ensures domain validation happens via Post aggregate.
    Zero or negative author_id values should raise ValueError from the
    Post.create_draft() method, preventing creation of drafts with
    invalid author references.
    """
    command = CreateDraftCommand(
        slug="valid-slug", title="Valid Title", author_id=0
    )

    with pytest.raises(ValueError, match="author_id"):
        create_draft_handler(
            command=command,
            draft_repo=draft_repository,
            post_repo=mock_post_repository,
            github_service=mock_github_service,
        )

    mock_post_repository.save.assert_not_called()
    mock_github_service.commit_file.assert_not_called()


def test_handler_raises_error_for_invalid_slug(
    draft_repository: FileSystemDraftRepository,
    mock_post_repository: Mock,
    mock_github_service: Mock,
) -> None:
    """Verify handler rejects invalid slug.

    This test ensures slug validation happens via Slug value object.
    Invalid slugs (empty, too long, special chars only) should raise
    ValueError when creating the Post aggregate, preventing creation
    of drafts with invalid slugs.
    """
    command = CreateDraftCommand(slug="", title="Valid Title", author_id=1)

    with pytest.raises(ValueError, match="Slug"):
        create_draft_handler(
            command=command,
            draft_repo=draft_repository,
            post_repo=mock_post_repository,
            github_service=mock_github_service,
        )

    mock_post_repository.save.assert_not_called()
    mock_github_service.commit_file.assert_not_called()


def test_handler_continues_if_github_commit_fails(
    draft_repository: FileSystemDraftRepository,
    mock_post_repository: Mock,
    mock_github_service: Mock,
) -> None:
    """Verify handler continues gracefully on GitHub failure.

    This test ensures resilience to GitHub API failures. If committing
    to GitHub fails (returns None), the handler should log a warning
    but continue with local operations. The draft should still be saved
    to filesystem and database.
    """
    mock_github_service.commit_file.return_value = None

    command = CreateDraftCommand(
        slug="resilient-post", title="Resilient Post", author_id=1
    )

    result = create_draft_handler(
        command=command,
        draft_repo=draft_repository,
        post_repo=mock_post_repository,
        github_service=mock_github_service,
    )

    assert result is not None
    assert str(result.slug) == "resilient-post"

    file_path = draft_repository.drafts_path / "resilient-post.md"
    assert file_path.exists()

    mock_post_repository.save.assert_called_once()


def test_handler_sets_created_at_to_current_time(
    draft_repository: FileSystemDraftRepository,
    mock_post_repository: Mock,
    mock_github_service: Mock,
) -> None:
    """Verify handler sets created_at to current UTC time.

    This test ensures audit trail requirements. The created Post should
    have a created_at timestamp set to the current UTC time (within 1
    second of handler execution). This timestamp must be recent and
    accurate.
    """
    before = datetime.now(dt.UTC)

    command = CreateDraftCommand(
        slug="timestamp-test", title="Timestamp Test", author_id=1
    )

    result = create_draft_handler(
        command=command,
        draft_repo=draft_repository,
        post_repo=mock_post_repository,
        github_service=mock_github_service,
    )

    after = datetime.now(dt.UTC)

    assert result is not None
    assert before <= result.created_at <= after
    assert (result.created_at - before).total_seconds() < 1


def test_handler_rolls_back_filesystem_on_database_failure(
    draft_repository: FileSystemDraftRepository,
    mock_post_repository: Mock,
    mock_github_service: Mock,
) -> None:
    """Verify handler rolls back filesystem changes on database failure.

    This test ensures atomicity of the draft creation process. If saving
    to the database fails after the filesystem write succeeds, the handler
    should delete the draft file that was created and re-raise the error.
    This prevents orphaned draft files without database records.
    """
    mock_post_repository.save.side_effect = ValueError("Database error")

    command = CreateDraftCommand(
        slug="rollback-test", title="Rollback Test", author_id=1
    )

    file_path = draft_repository.drafts_path / "rollback-test.md"

    with pytest.raises(ValueError, match="Database error"):
        create_draft_handler(
            command=command,
            draft_repo=draft_repository,
            post_repo=mock_post_repository,
            github_service=mock_github_service,
        )

    assert not file_path.exists()
