"""Unit tests for save_draft_handler.

This module defines comprehensive unit tests for the save_draft_handler
following TDD Red phase principles. These tests will initially fail until
the handler is implemented.

Test Coverage:
- Happy path: successful save with GitHub commit (2 tests)
- Error cases: draft not found, GitHub failure (2 tests)
- Corruption recovery: GitHub success, GitHub fails, GitHub also
  corrupted (3 tests)
- Edge cases: empty content (1 test)

Total: 8+ unit tests
"""

from datetime import UTC, datetime
from unittest.mock import Mock, patch

import pytest

from backend.application.commands.handlers.save_draft_handler import (
    save_draft_handler,
)
from backend.application.commands.save_draft_command import SaveDraftCommand
from backend.infrastructure.persistence.filesystem_draft_repository import (
    DraftFile,
)


@pytest.fixture
def mock_draft_repo() -> Mock:
    """Fixture providing mock FileSystemDraftRepository."""
    mock = Mock()
    mock.find_by_slug.return_value = DraftFile(
        slug="test-post",
        title="Test Post",
        author="user123",
        content="Original content",
        published=False,
        created_at=datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC),
    )
    return mock


@pytest.fixture
def mock_github_service() -> Mock:
    """Fixture providing mock GitHubSyncService."""
    mock = Mock()
    mock.commit_file.return_value = "abc123"
    mock.get_file_content.return_value = None
    return mock


@pytest.fixture
def mock_post_repo() -> Mock:
    """Fixture providing mock PostRepository for authorization checks."""
    from backend.domain.aggregates.post import Post

    mock = Mock()
    post = Post.create_draft(slug="test-post", title="Test Post", author_id=1)
    mock.find_by_slug.return_value = post
    return mock


def test_save_draft_handler_success(
    mock_draft_repo: Mock, mock_post_repo: Mock, mock_github_service: Mock
) -> None:
    """Verify handler updates content and commits to GitHub successfully.

    This is the happy path test. The handler should:
    1. Load existing draft via find_by_slug
    2. Update draft content with command.content
    3. Save updated draft to filesystem
    4. Commit to GitHub with "Update draft: {title}" message
    5. Return None (void function)

    All operations should succeed without errors.
    """
    command = SaveDraftCommand(
        slug="test-post",
        content="Updated content with new changes",
        author_id=1,
        user_role="author",
    )

    save_draft_handler(
        command=command,
        draft_repo=mock_draft_repo,
        post_repo=mock_post_repo,
        github_service=mock_github_service,
    )

    mock_draft_repo.find_by_slug.assert_called_once_with("test-post")

    save_call_args = mock_draft_repo.save.call_args
    assert save_call_args is not None
    saved_draft = save_call_args[0][0]
    assert saved_draft.content == "Updated content with new changes"
    assert saved_draft.slug == "test-post"
    assert saved_draft.title == "Test Post"
    assert saved_draft.author == "user123"

    commit_call_args = mock_github_service.commit_file.call_args
    assert commit_call_args is not None
    assert commit_call_args[1]["path"] == "drafts/test-post.md"
    assert "Update draft: Test Post" in commit_call_args[1]["message"]
    assert "Updated content with new changes" in commit_call_args[1]["content"]


def test_save_draft_handler_preserves_front_matter(
    mock_draft_repo: Mock, mock_post_repo: Mock, mock_github_service: Mock
) -> None:
    """Verify handler preserves title, author, created_at when updating.

    This test ensures only the content field is updated. All metadata
    fields (title, author, created_at, published) should remain unchanged
    from the original draft file.
    """
    original_draft = DraftFile(
        slug="preserve-test",
        title="Original Title",
        author="original-author",
        content="Original content",
        published=False,
        created_at=datetime(2024, 12, 15, 10, 30, 0, tzinfo=UTC),
        tags=["python", "testing"],
    )
    mock_draft_repo.find_by_slug.return_value = original_draft

    command = SaveDraftCommand(
        slug="preserve-test",
        content="Only content changed",
        author_id=1,
        user_role="author",
    )

    save_draft_handler(
        command=command,
        draft_repo=mock_draft_repo,
        post_repo=mock_post_repo,
        github_service=mock_github_service,
    )

    save_call_args = mock_draft_repo.save.call_args
    assert save_call_args is not None
    saved_draft = save_call_args[0][0]

    assert saved_draft.title == "Original Title"
    assert saved_draft.author == "original-author"
    assert saved_draft.created_at == datetime(
        2024, 12, 15, 10, 30, 0, tzinfo=UTC
    )
    assert saved_draft.published is False
    assert saved_draft.tags == ["python", "testing"]
    assert saved_draft.content == "Only content changed"


def test_save_draft_handler_draft_not_found(
    mock_draft_repo: Mock, mock_post_repo: Mock, mock_github_service: Mock
) -> None:
    """Verify handler raises ValueError when draft doesn't exist.

    This test ensures error handling for missing drafts. If find_by_slug
    returns None, the handler should raise ValueError with a clear message
    indicating the draft was not found. No save or GitHub operations should
    occur.
    """
    mock_draft_repo.find_by_slug.return_value = None

    command = SaveDraftCommand(
        slug="nonexistent",
        content="New content",
        author_id=1,
        user_role="author",
    )

    with pytest.raises(ValueError, match="not found|does not exist"):
        save_draft_handler(
            command=command,
            draft_repo=mock_draft_repo,
            post_repo=mock_post_repo,
            github_service=mock_github_service,
        )

    mock_draft_repo.find_by_slug.assert_called_once_with("nonexistent")
    mock_draft_repo.save.assert_not_called()
    mock_github_service.commit_file.assert_not_called()


@patch("backend.application.commands.handlers.save_draft_handler.logger")
def test_save_draft_handler_github_failure_continues(
    mock_logger: Mock,
    mock_draft_repo: Mock,
    mock_post_repo: Mock,
    mock_github_service: Mock,
) -> None:
    """Verify handler continues gracefully when GitHub commit fails.

    This test ensures resilience to GitHub API failures. If commit_file
    returns None (failure), the handler should:
    1. Log a warning about the GitHub failure
    2. Continue execution (not raise exception)
    3. Still save the draft locally

    The local save must complete successfully despite GitHub failure.
    """
    mock_github_service.commit_file.return_value = None

    command = SaveDraftCommand(
        slug="test-post",
        content="Content despite GitHub failure",
        author_id=1,
        user_role="author",
    )

    save_draft_handler(
        command=command,
        draft_repo=mock_draft_repo,
        post_repo=mock_post_repo,
        github_service=mock_github_service,
    )

    mock_draft_repo.save.assert_called_once()
    mock_github_service.commit_file.assert_called_once()
    mock_logger.warning.assert_called_once()

    warning_call = mock_logger.warning.call_args[0][0]
    assert "github" in warning_call.lower() or "commit" in warning_call.lower()


def test_save_draft_handler_corruption_github_success(
    mock_draft_repo: Mock, mock_post_repo: Mock, mock_github_service: Mock
) -> None:
    """Verify handler recovers from corrupted file using GitHub.

    This test ensures corruption recovery flow works. When find_by_slug
    raises ValueError (corrupted file), the handler should:
    1. Call _recover_from_corruption helper
    2. Fetch content from GitHub via get_file_content
    3. Parse GitHub content and save locally
    4. Continue with normal save flow using recovered draft

    The save should complete successfully after recovery.

    Note: The DraftFile object is mutated between saves, so we capture
    the content values at each save point using a side_effect.
    """
    mock_draft_repo.find_by_slug.side_effect = ValueError(
        "Invalid front matter"
    )

    github_content = """---
title: Recovered Post
author: user456
created_at: '2025-01-10T15:00:00+00:00'
published: false
tags: []
---

Recovered content from GitHub"""

    mock_github_service.get_file_content.return_value = github_content

    saved_contents = []

    def capture_save(draft: DraftFile) -> None:
        saved_contents.append(
            {
                "title": draft.title,
                "author": draft.author,
                "content": draft.content,
                "slug": draft.slug,
            }
        )

    mock_draft_repo.save.side_effect = capture_save

    command = SaveDraftCommand(
        slug="corrupted-post",
        content="New content after recovery",
        author_id=1,
        user_role="author",
    )

    save_draft_handler(
        command=command,
        draft_repo=mock_draft_repo,
        post_repo=mock_post_repo,
        github_service=mock_github_service,
    )

    mock_github_service.get_file_content.assert_called_once_with(
        "drafts/corrupted-post.md"
    )

    assert mock_draft_repo.save.call_count == 2
    assert len(saved_contents) == 2

    first_save = saved_contents[0]
    assert first_save["title"] == "Recovered Post"
    assert first_save["author"] == "user456"
    assert first_save["content"] == "Recovered content from GitHub"

    second_save = saved_contents[1]
    assert second_save["content"] == "New content after recovery"


def test_save_draft_handler_corruption_github_fails(
    mock_draft_repo: Mock, mock_post_repo: Mock, mock_github_service: Mock
) -> None:
    """Verify handler creates new draft when GitHub recovery fails.

    This test ensures fallback recovery when both local file and GitHub
    are unavailable. When find_by_slug raises ValueError (corruption) and
    get_file_content returns None (GitHub failure), the handler should:
    1. Create a new draft with default metadata
    2. Use "Recovered: {slug}" as title
    3. Set author to "unknown"
    4. Set created_at to current time
    5. Continue with normal save flow

    The save should complete successfully with new draft.

    Note: The DraftFile object is mutated between saves, so we capture
    the content values at each save point using a side_effect.
    """
    mock_draft_repo.find_by_slug.side_effect = ValueError("Corrupted file")
    mock_github_service.get_file_content.return_value = None

    saved_contents = []

    def capture_save(draft: DraftFile) -> None:
        saved_contents.append(
            {
                "slug": draft.slug,
                "title": draft.title,
                "author": draft.author,
                "content": draft.content,
                "published": draft.published,
            }
        )

    mock_draft_repo.save.side_effect = capture_save

    command = SaveDraftCommand(
        slug="recovery-fallback",
        content="Content for new draft",
        author_id=1,
        user_role="author",
    )

    save_draft_handler(
        command=command,
        draft_repo=mock_draft_repo,
        post_repo=mock_post_repo,
        github_service=mock_github_service,
    )

    assert mock_draft_repo.save.call_count == 2
    assert len(saved_contents) == 2

    first_save = saved_contents[0]
    assert first_save["slug"] == "recovery-fallback"
    assert first_save["title"] == "Recovered: recovery-fallback"
    assert first_save["author"] == "unknown"
    assert first_save["content"] == ""
    assert first_save["published"] is False

    second_save = saved_contents[1]
    assert second_save["content"] == "Content for new draft"


def test_save_draft_handler_corruption_github_also_corrupted(
    mock_draft_repo: Mock, mock_post_repo: Mock, mock_github_service: Mock
) -> None:
    """Verify handler creates new draft when GitHub content is also corrupted.

    This test ensures fallback recovery when both local and GitHub files
    are corrupted. When find_by_slug raises ValueError and get_file_content
    returns invalid YAML, the handler should:
    1. Attempt to parse GitHub content
    2. Catch the parsing error
    3. Fall back to creating new draft with "Recovered: {slug}" title
    4. Continue with normal save flow

    The save should complete successfully despite double corruption.

    Note: The DraftFile object is mutated between saves, so we capture
    the content values at each save point using a side_effect.
    """
    mock_draft_repo.find_by_slug.side_effect = ValueError(
        "Corrupted local file"
    )

    invalid_github_content = (
        "This is not valid YAML front matter\nJust plain text"
    )
    mock_github_service.get_file_content.return_value = invalid_github_content

    saved_contents = []

    def capture_save(draft: DraftFile) -> None:
        saved_contents.append(
            {
                "slug": draft.slug,
                "title": draft.title,
                "author": draft.author,
                "content": draft.content,
            }
        )

    mock_draft_repo.save.side_effect = capture_save

    command = SaveDraftCommand(
        slug="double-corruption",
        content="Content despite double corruption",
        author_id=1,
        user_role="author",
    )

    save_draft_handler(
        command=command,
        draft_repo=mock_draft_repo,
        post_repo=mock_post_repo,
        github_service=mock_github_service,
    )

    assert mock_draft_repo.save.call_count == 2
    assert len(saved_contents) == 2

    first_save = saved_contents[0]
    assert first_save["slug"] == "double-corruption"
    assert first_save["title"] == "Recovered: double-corruption"
    assert first_save["author"] == "unknown"

    second_save = saved_contents[1]
    assert second_save["content"] == "Content despite double corruption"


def test_save_draft_handler_empty_content(
    mock_draft_repo: Mock, mock_post_repo: Mock, mock_github_service: Mock
) -> None:
    """Verify handler accepts empty content string.

    This test ensures edge case handling for empty content. An empty string
    is a valid content value and should be accepted. The handler should save
    the draft with empty content and commit to GitHub normally.
    """
    command = SaveDraftCommand(
        slug="test-post",
        content="",
        author_id=1,
        user_role="author",
    )

    save_draft_handler(
        command=command,
        draft_repo=mock_draft_repo,
        post_repo=mock_post_repo,
        github_service=mock_github_service,
    )

    save_call_args = mock_draft_repo.save.call_args
    assert save_call_args is not None
    saved_draft = save_call_args[0][0]
    assert saved_draft.content == ""

    mock_github_service.commit_file.assert_called_once()


def test_save_draft_handler_updates_existing_draft_metadata(
    mock_draft_repo: Mock, mock_post_repo: Mock, mock_github_service: Mock
) -> None:
    """Verify handler preserves published_at and other optional metadata.

    This test ensures all optional fields are preserved during update.
    If a draft has published_at set, it should remain after content update.
    """
    published_draft = DraftFile(
        slug="published-draft",
        title="Published Draft",
        author="author123",
        content="Original published content",
        published=True,
        created_at=datetime(2024, 11, 1, 10, 0, 0, tzinfo=UTC),
        published_at=datetime(2024, 11, 15, 14, 30, 0, tzinfo=UTC),
        tags=["release", "important"],
    )
    mock_draft_repo.find_by_slug.return_value = published_draft

    command = SaveDraftCommand(
        slug="published-draft",
        content="Updated published content",
        author_id=1,
        user_role="author",
    )

    save_draft_handler(
        command=command,
        draft_repo=mock_draft_repo,
        post_repo=mock_post_repo,
        github_service=mock_github_service,
    )

    save_call_args = mock_draft_repo.save.call_args
    assert save_call_args is not None
    saved_draft = save_call_args[0][0]

    assert saved_draft.published is True
    assert saved_draft.published_at == datetime(
        2024, 11, 15, 14, 30, 0, tzinfo=UTC
    )
    assert saved_draft.tags == ["release", "important"]
    assert saved_draft.content == "Updated published content"


def test_save_draft_handler_github_commit_includes_full_content(
    mock_draft_repo: Mock, mock_post_repo: Mock, mock_github_service: Mock
) -> None:
    """Verify GitHub commit includes YAML front matter and content.

    This test ensures the GitHub commit contains the complete markdown file
    with YAML front matter. The commit content should be the result of
    to_markdown() with all metadata and updated content.
    """
    command = SaveDraftCommand(
        slug="test-post",
        content="# New Content\n\nWith markdown formatting",
        author_id=1,
        user_role="author",
    )

    save_draft_handler(
        command=command,
        draft_repo=mock_draft_repo,
        post_repo=mock_post_repo,
        github_service=mock_github_service,
    )

    commit_call_args = mock_github_service.commit_file.call_args
    assert commit_call_args is not None

    committed_content = commit_call_args[1]["content"]

    assert committed_content.startswith("---\n")
    assert "title: Test Post" in committed_content
    assert "author: user123" in committed_content
    assert (
        "published: false" in committed_content
        or "published: False" in committed_content
    )
    assert "# New Content\n\nWith markdown formatting" in committed_content
