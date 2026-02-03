"""Integration tests for save_draft_handler with real filesystem operations.

This module defines comprehensive integration tests for the save_draft_handler
following TDD Red phase principles. These tests use REAL filesystem operations
with temporary directories to verify actual file I/O behavior.

Test Coverage:
- Happy path: successful save with file updates (2 tests)
- Error cases: draft not found on filesystem (1 test)
- Corruption recovery: GitHub success, GitHub fails (2 tests)
- Edge cases: large content within limits (1 test)

Total: 6 integration tests

Key Differences from Unit Tests:
- Uses REAL FileSystemDraftRepository with temp directory
- Mocks ONLY GitHubSyncService (no real GitHub API calls)
- Performs ACTUAL file I/O to verify filesystem behavior
- Reads and parses ACTUAL YAML front matter from files
"""

import tempfile
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import Mock

import pytest

from backend.application.commands.handlers.save_draft_handler import (
    save_draft_handler,
)
from backend.application.commands.save_draft_command import SaveDraftCommand
from backend.infrastructure.persistence.filesystem_draft_repository import (
    DraftFile,
    FileSystemDraftRepository,
)


@pytest.fixture
def temp_drafts_dir():
    """Create temporary directory for draft files.

    This fixture provides a real temporary directory that is automatically
    cleaned up after each test. All file operations during the test will
    use this directory.

    Yields:
        Path: Temporary directory path for draft files
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def draft_repo(temp_drafts_dir: Path) -> FileSystemDraftRepository:
    """Real FileSystemDraftRepository with temp directory.

    This fixture creates a real repository instance that performs actual
    file I/O operations in the temporary directory. No mocking is used
    for filesystem operations.

    Args:
        temp_drafts_dir: Temporary directory from fixture

    Returns:
        FileSystemDraftRepository: Real repository instance
    """
    return FileSystemDraftRepository(drafts_path=temp_drafts_dir)


@pytest.fixture
def mock_github_service() -> Mock:
    """Mocked GitHub service to avoid real API calls.

    This fixture provides a mock that simulates successful GitHub operations
    without making actual API calls. The default behavior simulates successful
    commits and no existing content on GitHub.

    Returns:
        Mock: Mocked GitHubSyncService instance
    """
    mock = Mock()
    mock.commit_file.return_value = "abc123"
    mock.get_file_content.return_value = None
    return mock


@pytest.fixture
def mock_post_repo() -> Mock:
    """Mock PostRepository that returns a post owned by author_id=1.

    This fixture provides a mock PostRepository for authorization checks
    in the save_draft_handler. All test commands use author_id=1, so
    the mock returns a matching Post aggregate.

    Returns:
        Mock: Mocked PostRepository instance
    """
    from backend.domain.aggregates.post import Post

    mock_repo = Mock()
    post = Post.create_draft(slug="test-post", title="Test Post", author_id=1)
    mock_repo.find_by_slug.return_value = post
    return mock_repo


@pytest.fixture
def sample_draft(draft_repo: FileSystemDraftRepository) -> DraftFile:
    """Create a sample draft file for testing.

    This fixture creates an actual draft file on the filesystem that can
    be used for update operations. The file is written with YAML front
    matter and can be read back during tests.

    Args:
        draft_repo: Real FileSystemDraftRepository instance

    Returns:
        DraftFile: Sample draft that exists on filesystem
    """
    draft = DraftFile(
        slug="test-post",
        title="Test Post",
        author="test@example.com",
        content="Original content",
        published=False,
        created_at=datetime(2025, 1, 1, tzinfo=UTC),
    )
    draft_repo.save(draft)
    return draft


def test_save_draft_updates_file_on_filesystem(
    draft_repo: FileSystemDraftRepository,
    mock_github_service: Mock,
    mock_post_repo: Mock,
    sample_draft: DraftFile,
    temp_drafts_dir: Path,
) -> None:
    """Verify handler actually updates file content on filesystem.

    This is the happy path integration test. The handler should:
    1. Read existing draft file from filesystem
    2. Update content field with new value
    3. Write updated draft back to filesystem
    4. Preserve all YAML front matter fields
    5. Commit to GitHub with updated content

    The test verifies by reading the actual file from disk after the save.
    """
    command = SaveDraftCommand(
        slug="test-post",
        content="Updated content with new changes",
        author_id=1,
        user_role="author",
    )

    save_draft_handler(
        command=command,
        draft_repo=draft_repo,
        github_service=mock_github_service,
        post_repo=mock_post_repo,
    )

    saved_draft = draft_repo.find_by_slug("test-post")
    assert saved_draft is not None
    assert saved_draft.content == "Updated content with new changes"
    assert saved_draft.title == "Test Post"
    assert saved_draft.author == "test@example.com"
    assert saved_draft.published is False
    assert saved_draft.created_at == datetime(2025, 1, 1, tzinfo=UTC)

    file_path = temp_drafts_dir / "test-post.md"
    assert file_path.exists()

    file_content = file_path.read_text(encoding="utf-8")
    assert "Updated content with new changes" in file_content
    assert "title: Test Post" in file_content

    mock_github_service.commit_file.assert_called_once()


def test_save_draft_preserves_yaml_front_matter(
    draft_repo: FileSystemDraftRepository,
    mock_post_repo: Mock,
    mock_github_service: Mock,
    temp_drafts_dir: Path,
) -> None:
    """Verify handler preserves YAML front matter after content update.

    This test creates a draft with complex front matter (tags, published_at)
    and verifies that only the content field changes. All metadata should
    remain identical after the save operation.
    """
    original_draft = DraftFile(
        slug="preserve-test",
        title="Original Title",
        author="original-author",
        content="Original content",
        published=True,
        created_at=datetime(2024, 12, 15, 10, 30, 0, tzinfo=UTC),
        published_at=datetime(2024, 12, 20, 14, 0, 0, tzinfo=UTC),
        tags=["python", "testing", "integration"],
    )
    draft_repo.save(original_draft)

    command = SaveDraftCommand(
        slug="preserve-test",
        content="Only content changed",
        author_id=1,
        user_role="author",
    )

    save_draft_handler(
        command=command,
        draft_repo=draft_repo,
        github_service=mock_github_service,
        post_repo=mock_post_repo,
    )

    saved_draft = draft_repo.find_by_slug("preserve-test")
    assert saved_draft is not None

    assert saved_draft.title == "Original Title"
    assert saved_draft.author == "original-author"
    assert saved_draft.created_at == datetime(
        2024, 12, 15, 10, 30, 0, tzinfo=UTC
    )
    assert saved_draft.published is True
    assert saved_draft.published_at == datetime(
        2024, 12, 20, 14, 0, 0, tzinfo=UTC
    )
    assert saved_draft.tags == ["python", "testing", "integration"]
    assert saved_draft.content == "Only content changed"

    file_path = temp_drafts_dir / "preserve-test.md"
    file_content = file_path.read_text(encoding="utf-8")
    assert "title: Original Title" in file_content
    assert "author: original-author" in file_content
    assert "Only content changed" in file_content


def test_save_draft_draft_not_found_on_filesystem(
    draft_repo: FileSystemDraftRepository,
    mock_post_repo: Mock,
    mock_github_service: Mock,
) -> None:
    """Verify handler raises ValueError when draft file doesn't exist.

    This test ensures error handling for missing drafts. When find_by_slug
    returns None (file doesn't exist), the handler should raise ValueError
    with a clear message. No save or GitHub operations should occur.
    """
    command = SaveDraftCommand(
        slug="nonexistent",
        content="New content",
        author_id=1,
        user_role="author",
    )

    with pytest.raises(ValueError, match="not found|does not exist"):
        save_draft_handler(
            command=command,
            draft_repo=draft_repo,
            post_repo=mock_post_repo,
            github_service=mock_github_service,
        )

    mock_github_service.commit_file.assert_not_called()


def test_save_draft_real_corruption_github_recovery(
    draft_repo: FileSystemDraftRepository,
    mock_post_repo: Mock,
    mock_github_service: Mock,
    temp_drafts_dir: Path,
) -> None:
    """Verify handler recovers from real corrupted file using GitHub.

    This test creates an ACTUAL corrupted YAML file on the filesystem and
    verifies the handler can recover by fetching valid content from GitHub.
    The recovery flow should:
    1. Attempt to read corrupted file (raises ValueError)
    2. Call GitHub API to fetch valid content
    3. Parse GitHub content and save to filesystem
    4. Continue with normal save operation
    """
    file_path = temp_drafts_dir / "corrupted.md"
    file_path.write_text("---\ninvalid: yaml: content:\n---\nContent")

    github_content = """---
title: Recovered Post
author: user456
created_at: '2025-01-10T15:00:00+00:00'
published: false
tags: []
---

Recovered content from GitHub"""

    mock_github_service.get_file_content.return_value = github_content

    command = SaveDraftCommand(
        slug="corrupted",
        content="New content after recovery",
        author_id=1,
        user_role="author",
    )

    save_draft_handler(
        command=command,
        draft_repo=draft_repo,
        github_service=mock_github_service,
        post_repo=mock_post_repo,
    )

    mock_github_service.get_file_content.assert_called_once_with(
        "drafts/corrupted.md"
    )

    saved_draft = draft_repo.find_by_slug("corrupted")
    assert saved_draft is not None
    assert saved_draft.title == "Recovered Post"
    assert saved_draft.author == "user456"
    assert saved_draft.content == "New content after recovery"

    file_content = file_path.read_text(encoding="utf-8")
    assert "title: Recovered Post" in file_content
    assert "New content after recovery" in file_content


def test_save_draft_real_corruption_github_fails(
    draft_repo: FileSystemDraftRepository,
    mock_post_repo: Mock,
    mock_github_service: Mock,
    temp_drafts_dir: Path,
) -> None:
    """Verify handler creates new draft when GitHub recovery fails.

    This test creates an ACTUAL corrupted YAML file and simulates GitHub
    returning None (failure to fetch). The handler should fall back to
    creating a new draft with default metadata.
    """
    file_path = temp_drafts_dir / "recovery-fallback.md"
    file_path.write_text("---\nbroken yaml here\n---\nContent")

    mock_github_service.get_file_content.return_value = None

    command = SaveDraftCommand(
        slug="recovery-fallback",
        content="Content for new draft",
        author_id=1,
        user_role="author",
    )

    save_draft_handler(
        command=command,
        draft_repo=draft_repo,
        github_service=mock_github_service,
        post_repo=mock_post_repo,
    )

    saved_draft = draft_repo.find_by_slug("recovery-fallback")
    assert saved_draft is not None
    assert saved_draft.slug == "recovery-fallback"
    assert saved_draft.title == "Recovered: recovery-fallback"
    assert saved_draft.author == "unknown"
    assert saved_draft.content == "Content for new draft"
    assert saved_draft.published is False

    file_content = file_path.read_text(encoding="utf-8")
    assert "title: 'Recovered: recovery-fallback'" in file_content
    assert "author: unknown" in file_content
    assert "Content for new draft" in file_content


def test_save_draft_large_content_within_limits(
    draft_repo: FileSystemDraftRepository,
    mock_post_repo: Mock,
    mock_github_service: Mock,
    sample_draft: DraftFile,
    temp_drafts_dir: Path,
) -> None:
    """Verify handler accepts content close to 10MB limit.

    This test ensures the handler can save large content successfully.
    Content at 9.5MB should be accepted and written to filesystem without
    errors. This verifies no hidden size limits exist in the file I/O.
    """
    large_content = "x" * 9_500_000

    command = SaveDraftCommand(
        slug="test-post",
        content=large_content,
        author_id=1,
        user_role="author",
    )

    save_draft_handler(
        command=command,
        draft_repo=draft_repo,
        github_service=mock_github_service,
        post_repo=mock_post_repo,
    )

    saved_draft = draft_repo.find_by_slug("test-post")
    assert saved_draft is not None
    assert len(saved_draft.content) == 9_500_000
    assert saved_draft.content == large_content

    file_path = temp_drafts_dir / "test-post.md"
    assert file_path.exists()

    file_size = file_path.stat().st_size
    assert file_size > 9_500_000

    mock_github_service.commit_file.assert_called_once()
