"""Unit tests for unpublish_post_handler.

This module defines comprehensive unit tests for the unpublish_post_handler
following TDD Red phase principles. These tests will initially fail until
the handler is implemented.

Test Coverage:
- Success path: unpublishing, database update, file update, GitHub
  commit (4 tests)
- Error cases: post not found, already unpublished, draft file not
  found (3 tests)
- Atomicity: database failures, resilience to file/GitHub failures
  (3 tests)
- Logging: info, debug, warnings (3 tests)
- Edge cases: preserves html_content, preserves published_at (2 tests)

Total: 15+ unit tests
"""

from datetime import UTC, datetime
from unittest.mock import Mock, patch

import pytest
from sqlalchemy.exc import IntegrityError

from backend.application.commands.handlers.unpublish_post_handler import (
    unpublish_post_handler,
)
from backend.application.commands.unpublish_post_command import (
    UnpublishPostCommand,
)
from backend.domain.aggregates.post import Post
from backend.exceptions import NotFoundError
from backend.infrastructure.persistence.filesystem_draft_repository import (
    DraftFile,
)


@pytest.fixture
def published_draft_file_fixture() -> DraftFile:
    """Fixture providing a published DraftFile."""
    return DraftFile(
        slug="test-post",
        title="Test Post Title",
        author="user123",
        content="# Test Content\n\nThis is **markdown** content.",
        published=True,
        published_at=datetime(2025, 1, 15, 14, 30, 0, tzinfo=UTC),
        created_at=datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC),
        tags=["testing", "python"],
    )


@pytest.fixture
def published_post_aggregate_fixture() -> Post:
    """Fixture providing a published Post aggregate."""
    post = Post.create_draft(
        slug="test-post", title="Test Post Title", author_id=1
    )
    post.publish(html_content="<h1>Test Content</h1>")
    return post


@pytest.fixture
def mock_draft_repo() -> Mock:
    """Fixture providing mock FileSystemDraftRepository."""
    return Mock()


@pytest.fixture
def mock_post_repo() -> Mock:
    """Fixture providing mock PostRepository."""
    return Mock()


@pytest.fixture
def mock_github_service() -> Mock:
    """Fixture providing mock GitHubSyncService."""
    return Mock()


def test_unpublish_updates_database_published_flag(
    published_draft_file_fixture: DraftFile,
    published_post_aggregate_fixture: Post,
    mock_draft_repo: Mock,
    mock_post_repo: Mock,
    mock_github_service: Mock,
) -> None:
    """Verify handler sets published=False in database.

    This test ensures the handler updates the Post aggregate's published
    flag to False. The handler should:
    1. Load post via find_by_slug
    2. Call post.unpublish() domain method
    3. Save updated post to database
    """
    mock_draft_repo.find_by_slug.return_value = published_draft_file_fixture
    mock_post_repo.find_by_id.return_value = published_post_aggregate_fixture
    mock_post_repo.save.return_value = published_post_aggregate_fixture
    mock_github_service.commit_file.return_value = "abc123"

    command = UnpublishPostCommand(post_id=1, author_id=1, user_role="author")

    result = unpublish_post_handler(
        command=command,
        draft_repo=mock_draft_repo,
        post_repo=mock_post_repo,
        github_service=mock_github_service,
    )

    assert result.published is False
    mock_post_repo.save.assert_called_once()
    saved_post = mock_post_repo.save.call_args[0][0]
    assert saved_post.published is False


def test_unpublish_preserves_html_content(
    published_draft_file_fixture: DraftFile,
    published_post_aggregate_fixture: Post,
    mock_draft_repo: Mock,
    mock_post_repo: Mock,
    mock_github_service: Mock,
) -> None:
    """Verify handler preserves html_content field.

    This test ensures unpublishing does not clear the html_content field.
    The rendered HTML should remain in the database for potential
    republishing without re-rendering.
    """
    original_html = published_post_aggregate_fixture.html_content
    mock_draft_repo.find_by_slug.return_value = published_draft_file_fixture
    mock_post_repo.find_by_id.return_value = published_post_aggregate_fixture
    mock_post_repo.save.return_value = published_post_aggregate_fixture
    mock_github_service.commit_file.return_value = "abc123"

    command = UnpublishPostCommand(post_id=1, author_id=1, user_role="author")

    result = unpublish_post_handler(
        command=command,
        draft_repo=mock_draft_repo,
        post_repo=mock_post_repo,
        github_service=mock_github_service,
    )

    assert result.html_content == original_html
    assert result.html_content is not None


def test_unpublish_preserves_published_at_timestamp(
    published_draft_file_fixture: DraftFile,
    published_post_aggregate_fixture: Post,
    mock_draft_repo: Mock,
    mock_post_repo: Mock,
    mock_github_service: Mock,
) -> None:
    """Verify handler preserves published_at timestamp.

    This test ensures unpublishing preserves the original publication
    timestamp. This maintains historical data for when the post was
    first published.
    """
    original_published_at = published_post_aggregate_fixture.published_at
    mock_draft_repo.find_by_slug.return_value = published_draft_file_fixture
    mock_post_repo.find_by_id.return_value = published_post_aggregate_fixture
    mock_post_repo.save.return_value = published_post_aggregate_fixture
    mock_github_service.commit_file.return_value = "abc123"

    command = UnpublishPostCommand(post_id=1, author_id=1, user_role="author")

    result = unpublish_post_handler(
        command=command,
        draft_repo=mock_draft_repo,
        post_repo=mock_post_repo,
        github_service=mock_github_service,
    )

    assert result.published_at == original_published_at
    assert result.published_at is not None


def test_unpublish_saves_to_database(
    published_draft_file_fixture: DraftFile,
    published_post_aggregate_fixture: Post,
    mock_draft_repo: Mock,
    mock_post_repo: Mock,
    mock_github_service: Mock,
) -> None:
    """Verify handler saves unpublished post to database.

    This test ensures the handler persists the unpublished post via
    post_repo.save(). The save should occur after unpublish() is called
    on the aggregate, ensuring unpublished state is persisted.
    """
    mock_draft_repo.find_by_slug.return_value = published_draft_file_fixture
    mock_post_repo.find_by_id.return_value = published_post_aggregate_fixture
    mock_post_repo.save.return_value = published_post_aggregate_fixture
    mock_github_service.commit_file.return_value = "abc123"

    command = UnpublishPostCommand(post_id=1, author_id=1, user_role="author")

    result = unpublish_post_handler(
        command=command,
        draft_repo=mock_draft_repo,
        post_repo=mock_post_repo,
        github_service=mock_github_service,
    )

    mock_post_repo.save.assert_called_once()
    saved_post = mock_post_repo.save.call_args[0][0]
    assert saved_post.published is False
    assert result == published_post_aggregate_fixture


def test_unpublish_updates_draft_front_matter(
    published_draft_file_fixture: DraftFile,
    published_post_aggregate_fixture: Post,
    mock_draft_repo: Mock,
    mock_post_repo: Mock,
    mock_github_service: Mock,
) -> None:
    """Verify handler updates draft front matter with unpublished status.

    This test ensures the handler updates the draft file's front matter
    to mark it as unpublished. The draft_repo should:
    1. Load draft initially (first find_by_slug call)
    2. Save updated draft with published=False
    """
    mock_draft_repo.find_by_slug.return_value = published_draft_file_fixture
    mock_post_repo.find_by_id.return_value = published_post_aggregate_fixture
    mock_post_repo.save.return_value = published_post_aggregate_fixture
    mock_github_service.commit_file.return_value = "abc123"

    command = UnpublishPostCommand(post_id=1, author_id=1, user_role="author")

    unpublish_post_handler(
        command=command,
        draft_repo=mock_draft_repo,
        post_repo=mock_post_repo,
        github_service=mock_github_service,
    )

    mock_draft_repo.find_by_slug.assert_called_once_with("test-post")
    mock_draft_repo.save.assert_called_once()

    saved_draft = mock_draft_repo.save.call_args[0][0]
    assert saved_draft.published is False


def test_unpublish_commits_to_github(
    published_draft_file_fixture: DraftFile,
    published_post_aggregate_fixture: Post,
    mock_draft_repo: Mock,
    mock_post_repo: Mock,
    mock_github_service: Mock,
) -> None:
    """Verify handler commits updated draft to GitHub.

    This test ensures the handler commits the updated draft file to
    GitHub with the correct path and commit message. The commit should
    include the updated front matter with unpublished status.
    """
    mock_draft_repo.find_by_slug.return_value = published_draft_file_fixture
    mock_post_repo.find_by_id.return_value = published_post_aggregate_fixture
    mock_post_repo.save.return_value = published_post_aggregate_fixture
    mock_github_service.commit_file.return_value = "abc123"

    command = UnpublishPostCommand(post_id=1, author_id=1, user_role="author")

    unpublish_post_handler(
        command=command,
        draft_repo=mock_draft_repo,
        post_repo=mock_post_repo,
        github_service=mock_github_service,
    )

    mock_github_service.commit_file.assert_called_once()
    commit_call = mock_github_service.commit_file.call_args

    assert commit_call[1]["path"] == "drafts/test-post.md"
    assert "unpublish" in commit_call[1]["message"].lower()


def test_unpublish_fails_when_post_not_found(
    mock_draft_repo: Mock,
    mock_post_repo: Mock,
    mock_github_service: Mock,
) -> None:
    """Verify handler raises NotFoundError when post doesn't exist in database.

    This test ensures error handling for missing posts. If find_by_id
    returns None, the handler should raise NotFoundError. No other
    services should be called.
    """
    mock_post_repo.find_by_id.return_value = None

    command = UnpublishPostCommand(post_id=99, author_id=1, user_role="author")

    with pytest.raises(NotFoundError, match="Post.*not found"):
        unpublish_post_handler(
            command=command,
            draft_repo=mock_draft_repo,
            post_repo=mock_post_repo,
            github_service=mock_github_service,
        )

    mock_post_repo.find_by_id.assert_called_once_with(99)
    mock_post_repo.save.assert_not_called()


def test_unpublish_fails_when_already_unpublished(
    mock_draft_repo: Mock,
    mock_post_repo: Mock,
    mock_github_service: Mock,
) -> None:
    """Verify handler raises ValueError when post already unpublished.

    This test ensures idempotency protection. If the post's published
    flag is already False, the handler should raise ValueError to prevent
    duplicate unpublishing operations.
    """
    unpublished_post = Post.create_draft(
        slug="already-unpublished", title="Unpublished Post", author_id=1
    )
    mock_post_repo.find_by_id.return_value = unpublished_post

    command = UnpublishPostCommand(post_id=2, author_id=1, user_role="author")

    with pytest.raises(ValueError, match="not published|already unpublished"):
        unpublish_post_handler(
            command=command,
            draft_repo=mock_draft_repo,
            post_repo=mock_post_repo,
            github_service=mock_github_service,
        )

    mock_post_repo.save.assert_not_called()


def test_unpublish_fails_on_database_save_failure(
    published_draft_file_fixture: DraftFile,
    published_post_aggregate_fixture: Post,
    mock_draft_repo: Mock,
    mock_post_repo: Mock,
    mock_github_service: Mock,
) -> None:
    """Verify handler raises on database save failure.

    This test ensures atomicity. If post_repo.save() raises IntegrityError,
    the handler should propagate the exception without attempting to update
    the draft file or commit to GitHub. Partial failures should not corrupt
    state.
    """
    mock_draft_repo.find_by_slug.return_value = published_draft_file_fixture
    mock_post_repo.find_by_id.return_value = published_post_aggregate_fixture
    mock_post_repo.save.side_effect = IntegrityError(
        "Database error", None, Exception("Database constraint violation")
    )

    command = UnpublishPostCommand(post_id=1, author_id=1, user_role="author")

    with pytest.raises(IntegrityError):
        unpublish_post_handler(
            command=command,
            draft_repo=mock_draft_repo,
            post_repo=mock_post_repo,
            github_service=mock_github_service,
        )

    mock_draft_repo.save.assert_not_called()
    mock_github_service.commit_file.assert_not_called()


@patch("backend.application.commands.handlers.unpublish_post_handler.logger")
def test_unpublish_continues_when_draft_file_not_found(
    mock_logger: Mock,
    published_post_aggregate_fixture: Post,
    mock_draft_repo: Mock,
    mock_post_repo: Mock,
    mock_github_service: Mock,
) -> None:
    """Verify handler continues when draft file not found.

    This test ensures resilience to missing draft files. If find_by_slug
    returns None for the draft, the handler should:
    1. Log a warning about the missing draft file
    2. Continue execution (not raise exception)
    3. Still unpublish in database
    4. Skip file write and GitHub commit

    The post is unpublished in the database, so the operation is
    considered successful despite missing draft file.
    """
    mock_draft_repo.find_by_slug.return_value = None
    mock_post_repo.find_by_id.return_value = published_post_aggregate_fixture
    mock_post_repo.save.return_value = published_post_aggregate_fixture

    command = UnpublishPostCommand(post_id=1, author_id=1, user_role="author")

    result = unpublish_post_handler(
        command=command,
        draft_repo=mock_draft_repo,
        post_repo=mock_post_repo,
        github_service=mock_github_service,
    )

    assert result.published is False
    mock_logger.warning.assert_called_once()
    warning_message = mock_logger.warning.call_args[0][0]
    assert (
        "draft" in warning_message.lower() or "file" in warning_message.lower()
    )

    mock_draft_repo.save.assert_not_called()
    mock_github_service.commit_file.assert_not_called()


@patch("backend.application.commands.handlers.unpublish_post_handler.logger")
def test_unpublish_continues_when_draft_file_write_fails(
    mock_logger: Mock,
    published_draft_file_fixture: DraftFile,
    published_post_aggregate_fixture: Post,
    mock_draft_repo: Mock,
    mock_post_repo: Mock,
    mock_github_service: Mock,
) -> None:
    """Verify handler continues when draft file write fails.

    This test ensures resilience to filesystem failures. If draft_repo.save()
    raises OSError, the handler should:
    1. Log a warning about the filesystem failure
    2. Continue execution (not raise exception)
    3. Skip the GitHub commit (only commits when draft save succeeds)

    The post is already unpublished in the database, so the operation is
    considered successful despite draft file failure.
    """
    mock_draft_repo.find_by_slug.return_value = published_draft_file_fixture
    mock_post_repo.find_by_id.return_value = published_post_aggregate_fixture
    mock_post_repo.save.return_value = published_post_aggregate_fixture
    mock_draft_repo.save.side_effect = OSError("Disk full")
    mock_github_service.commit_file.return_value = "abc123"

    command = UnpublishPostCommand(post_id=1, author_id=1, user_role="author")

    result = unpublish_post_handler(
        command=command,
        draft_repo=mock_draft_repo,
        post_repo=mock_post_repo,
        github_service=mock_github_service,
    )

    assert result.published is False
    mock_logger.warning.assert_called_once()
    warning_message = mock_logger.warning.call_args[0][0]
    assert (
        "draft" in warning_message.lower() or "file" in warning_message.lower()
    )

    mock_github_service.commit_file.assert_not_called()


@patch("backend.application.commands.handlers.unpublish_post_handler.logger")
def test_unpublish_continues_when_github_commit_fails(
    mock_logger: Mock,
    published_draft_file_fixture: DraftFile,
    published_post_aggregate_fixture: Post,
    mock_draft_repo: Mock,
    mock_post_repo: Mock,
    mock_github_service: Mock,
) -> None:
    """Verify handler continues when GitHub commit fails.

    This test ensures resilience to GitHub API failures. If commit_file()
    returns None (failure), the handler should:
    1. Log a warning about the GitHub failure
    2. Continue execution (not raise exception)
    3. Return successfully unpublished post

    The post is already unpublished in the database, so the operation is
    considered successful despite GitHub failure.
    """
    mock_draft_repo.find_by_slug.return_value = published_draft_file_fixture
    mock_post_repo.find_by_id.return_value = published_post_aggregate_fixture
    mock_post_repo.save.return_value = published_post_aggregate_fixture
    mock_github_service.commit_file.return_value = None

    command = UnpublishPostCommand(post_id=1, author_id=1, user_role="author")

    result = unpublish_post_handler(
        command=command,
        draft_repo=mock_draft_repo,
        post_repo=mock_post_repo,
        github_service=mock_github_service,
    )

    assert result.published is False
    mock_logger.warning.assert_called_once()
    warning_message = mock_logger.warning.call_args[0][0]
    assert (
        "github" in warning_message.lower()
        or "commit" in warning_message.lower()
    )


@patch("backend.application.commands.handlers.unpublish_post_handler.logger")
def test_unpublish_logs_info_on_success(
    mock_logger: Mock,
    published_draft_file_fixture: DraftFile,
    published_post_aggregate_fixture: Post,
    mock_draft_repo: Mock,
    mock_post_repo: Mock,
    mock_github_service: Mock,
) -> None:
    """Verify handler logs INFO messages on success.

    This test ensures proper logging for audit trail. The handler should
    log INFO level messages containing:
    - "Unpublishing post" or similar at start
    - "unpublished" or similar on completion
    """
    mock_draft_repo.find_by_slug.return_value = published_draft_file_fixture
    mock_post_repo.find_by_id.return_value = published_post_aggregate_fixture
    mock_post_repo.save.return_value = published_post_aggregate_fixture
    mock_github_service.commit_file.return_value = "abc123"

    command = UnpublishPostCommand(post_id=1, author_id=1, user_role="author")

    unpublish_post_handler(
        command=command,
        draft_repo=mock_draft_repo,
        post_repo=mock_post_repo,
        github_service=mock_github_service,
    )

    assert mock_logger.info.call_count >= 1
    info_messages = [call[0][0] for call in mock_logger.info.call_args_list]
    assert any("unpublish" in msg.lower() for msg in info_messages)


@patch("backend.application.commands.handlers.unpublish_post_handler.logger")
def test_unpublish_logs_debug_steps(
    mock_logger: Mock,
    published_draft_file_fixture: DraftFile,
    published_post_aggregate_fixture: Post,
    mock_draft_repo: Mock,
    mock_post_repo: Mock,
    mock_github_service: Mock,
) -> None:
    """Verify handler logs DEBUG messages for processing steps.

    This test ensures detailed logging for debugging. The handler should
    log DEBUG level messages for:
    - Database update step
    - Draft file update step
    """
    mock_draft_repo.find_by_slug.return_value = published_draft_file_fixture
    mock_post_repo.find_by_id.return_value = published_post_aggregate_fixture
    mock_post_repo.save.return_value = published_post_aggregate_fixture
    mock_github_service.commit_file.return_value = "abc123"

    command = UnpublishPostCommand(post_id=1, author_id=1, user_role="author")

    unpublish_post_handler(
        command=command,
        draft_repo=mock_draft_repo,
        post_repo=mock_post_repo,
        github_service=mock_github_service,
    )

    debug_messages = [call[0][0] for call in mock_logger.debug.call_args_list]
    assert any(
        "database" in msg.lower() or "save" in msg.lower()
        for msg in debug_messages
    )


@patch("backend.application.commands.handlers.unpublish_post_handler.logger")
def test_unpublish_logs_warnings_on_partial_failure(
    mock_logger: Mock,
    published_draft_file_fixture: DraftFile,
    published_post_aggregate_fixture: Post,
    mock_draft_repo: Mock,
    mock_post_repo: Mock,
    mock_github_service: Mock,
) -> None:
    """Verify handler logs WARNING on partial failures.

    This test ensures proper warning logging when best-effort operations
    fail. When draft file write fails (OSError), the handler should:
    - Log exactly one WARNING about the draft/file failure
    - Skip the GitHub commit entirely (only runs after successful draft save)
    """
    mock_draft_repo.find_by_slug.return_value = published_draft_file_fixture
    mock_post_repo.find_by_id.return_value = published_post_aggregate_fixture
    mock_post_repo.save.return_value = published_post_aggregate_fixture
    mock_draft_repo.save.side_effect = OSError("Disk full")
    mock_github_service.commit_file.return_value = None

    command = UnpublishPostCommand(post_id=1, author_id=1, user_role="author")

    unpublish_post_handler(
        command=command,
        draft_repo=mock_draft_repo,
        post_repo=mock_post_repo,
        github_service=mock_github_service,
    )

    assert mock_logger.warning.call_count == 1
    warning_message = mock_logger.warning.call_args[0][0]
    assert (
        "draft" in warning_message.lower() or "file" in warning_message.lower()
    )
    mock_github_service.commit_file.assert_not_called()
