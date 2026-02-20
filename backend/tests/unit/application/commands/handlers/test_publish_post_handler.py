"""Unit tests for publish_post_handler.

This module defines comprehensive unit tests for the publish_post_handler
following TDD Red phase principles. These tests will initially fail until
the handler is implemented.

Test Coverage:
- Success path: rendering, sanitization, publishing (4 tests)
- Error cases: draft not found, already published, post not found (3 tests)
- Atomicity: database failures, file write failures, GitHub failures (3 tests)
- Logging: info, debug, warnings (3 tests)
- Edge cases: empty content, unicode, value objects (3 tests)

Total: 16+ unit tests
"""

from datetime import UTC, datetime
from unittest.mock import Mock, patch

import pytest
from sqlalchemy.exc import IntegrityError

from backend.application.commands.handlers.publish_post_handler import (
    publish_post_handler,
)
from backend.application.commands.publish_post_command import PublishPostCommand
from backend.domain.aggregates.post import Post
from backend.domain.value_objects.html_content import HtmlContent
from backend.infrastructure.persistence.filesystem_draft_repository import (
    DraftFile,
)


@pytest.fixture
def draft_file_fixture() -> DraftFile:
    """Fixture providing a DraftFile with markdown content."""
    return DraftFile(
        slug="test-post",
        title="Test Post Title",
        author="user123",
        content="# Test Content\n\nThis is **markdown** content.",
        published=False,
        created_at=datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC),
        tags=["testing", "python"],
    )


@pytest.fixture
def post_aggregate_fixture() -> Post:
    """Fixture providing a Post aggregate."""
    return Post.create_draft(
        slug="test-post", title="Test Post Title", author_id=1
    )


@pytest.fixture
def sanitized_html_fixture() -> str:
    """Fixture providing sanitized HTML content."""
    return (
        "<h1>Test Content</h1>\n"
        "<p>This is <strong>markdown</strong> content.</p>"
    )


@pytest.fixture
def mock_draft_repo() -> Mock:
    """Fixture providing mock FileSystemDraftRepository."""
    return Mock()


@pytest.fixture
def mock_post_repo() -> Mock:
    """Fixture providing mock PostRepository."""
    return Mock()


@pytest.fixture
def mock_markdown_service() -> Mock:
    """Fixture providing mock MarkdownRenderingService."""
    return Mock()


@pytest.fixture
def mock_html_sanitizer() -> Mock:
    """Fixture providing mock HtmlSanitizer."""
    return Mock()


@pytest.fixture
def mock_github_service() -> Mock:
    """Fixture providing mock GitHubSyncService."""
    return Mock()


def test_publish_renders_markdown_and_sanitizes_html(
    draft_file_fixture: DraftFile,
    post_aggregate_fixture: Post,
    sanitized_html_fixture: str,
    mock_draft_repo: Mock,
    mock_post_repo: Mock,
    mock_markdown_service: Mock,
    mock_html_sanitizer: Mock,
    mock_github_service: Mock,
) -> None:
    """Verify handler renders markdown and sanitizes HTML.

    This test ensures the markdown rendering and sanitization pipeline
    executes correctly. The handler should:
    1. Load draft via find_by_slug
    2. Render markdown content to raw HTML
    3. Sanitize raw HTML to safe HTML
    4. Return post with sanitized HTML
    """
    mock_draft_repo.find_by_slug.return_value = draft_file_fixture
    mock_post_repo.find_by_slug.return_value = post_aggregate_fixture
    mock_markdown_service.render.return_value = (
        "<h1>Test Content</h1>\n<p>Raw HTML</p>"
    )
    mock_html_sanitizer.sanitize.return_value = sanitized_html_fixture
    mock_post_repo.save.return_value = post_aggregate_fixture
    mock_github_service.commit_file.return_value = "abc123"

    command = PublishPostCommand(
        slug="test-post", author_id=1, user_role="author"
    )

    result = publish_post_handler(
        command=command,
        draft_repo=mock_draft_repo,
        post_repo=mock_post_repo,
        markdown_service=mock_markdown_service,
        html_sanitizer=mock_html_sanitizer,
        github_service=mock_github_service,
    )

    mock_markdown_service.render.assert_called_once_with(
        "# Test Content\n\nThis is **markdown** content."
    )
    mock_html_sanitizer.sanitize.assert_called_once_with(
        "<h1>Test Content</h1>\n<p>Raw HTML</p>"
    )
    assert result.html_content is not None
    assert result.html_content.value == sanitized_html_fixture


def test_publish_calls_post_domain_method(
    draft_file_fixture: DraftFile,
    post_aggregate_fixture: Post,
    sanitized_html_fixture: str,
    mock_draft_repo: Mock,
    mock_post_repo: Mock,
    mock_markdown_service: Mock,
    mock_html_sanitizer: Mock,
    mock_github_service: Mock,
) -> None:
    """Verify handler calls post.publish() domain method.

    This test ensures the handler delegates publishing logic to the
    Post aggregate's publish() method. The aggregate should:
    - Set published = True
    - Set published_at timestamp
    - Store sanitized HTML content
    """
    mock_draft_repo.find_by_slug.return_value = draft_file_fixture
    mock_post_repo.find_by_slug.return_value = post_aggregate_fixture
    mock_markdown_service.render.return_value = "<p>Raw HTML</p>"
    mock_html_sanitizer.sanitize.return_value = sanitized_html_fixture
    mock_post_repo.save.return_value = post_aggregate_fixture
    mock_github_service.commit_file.return_value = "abc123"

    command = PublishPostCommand(
        slug="test-post", author_id=1, user_role="author"
    )

    result = publish_post_handler(
        command=command,
        draft_repo=mock_draft_repo,
        post_repo=mock_post_repo,
        markdown_service=mock_markdown_service,
        html_sanitizer=mock_html_sanitizer,
        github_service=mock_github_service,
    )

    assert result.published is True
    assert result.published_at is not None
    assert result.html_content is not None


def test_publish_saves_to_database(
    draft_file_fixture: DraftFile,
    post_aggregate_fixture: Post,
    sanitized_html_fixture: str,
    mock_draft_repo: Mock,
    mock_post_repo: Mock,
    mock_markdown_service: Mock,
    mock_html_sanitizer: Mock,
    mock_github_service: Mock,
) -> None:
    """Verify handler saves published post to database.

    This test ensures the handler persists the published post via
    post_repo.save(). The save should occur after publish() is called
    on the aggregate, ensuring published state is persisted.
    """
    mock_draft_repo.find_by_slug.return_value = draft_file_fixture
    mock_post_repo.find_by_slug.return_value = post_aggregate_fixture
    mock_markdown_service.render.return_value = "<p>Raw HTML</p>"
    mock_html_sanitizer.sanitize.return_value = sanitized_html_fixture
    mock_post_repo.save.return_value = post_aggregate_fixture
    mock_github_service.commit_file.return_value = "abc123"

    command = PublishPostCommand(
        slug="test-post", author_id=1, user_role="author"
    )

    result = publish_post_handler(
        command=command,
        draft_repo=mock_draft_repo,
        post_repo=mock_post_repo,
        markdown_service=mock_markdown_service,
        html_sanitizer=mock_html_sanitizer,
        github_service=mock_github_service,
    )

    mock_post_repo.save.assert_called_once()
    saved_post = mock_post_repo.save.call_args[0][0]
    assert saved_post.published is True
    assert result == post_aggregate_fixture


def test_publish_updates_draft_front_matter(
    draft_file_fixture: DraftFile,
    post_aggregate_fixture: Post,
    sanitized_html_fixture: str,
    mock_draft_repo: Mock,
    mock_post_repo: Mock,
    mock_markdown_service: Mock,
    mock_html_sanitizer: Mock,
    mock_github_service: Mock,
) -> None:
    """Verify handler updates draft front matter with published status.

    This test ensures the handler updates the draft file's front matter
    to mark it as published. The draft_repo should:
    1. Load draft initially (first find_by_slug call)
    2. Save updated draft with published=True and published_at timestamp
    """
    mock_draft_repo.find_by_slug.return_value = draft_file_fixture
    mock_post_repo.find_by_slug.return_value = post_aggregate_fixture
    mock_markdown_service.render.return_value = "<p>Raw HTML</p>"
    mock_html_sanitizer.sanitize.return_value = sanitized_html_fixture
    mock_post_repo.save.return_value = post_aggregate_fixture
    mock_github_service.commit_file.return_value = "abc123"

    command = PublishPostCommand(
        slug="test-post", author_id=1, user_role="author"
    )

    publish_post_handler(
        command=command,
        draft_repo=mock_draft_repo,
        post_repo=mock_post_repo,
        markdown_service=mock_markdown_service,
        html_sanitizer=mock_html_sanitizer,
        github_service=mock_github_service,
    )

    mock_draft_repo.find_by_slug.assert_called_once_with("test-post")
    mock_draft_repo.save.assert_called_once()

    saved_draft = mock_draft_repo.save.call_args[0][0]
    assert saved_draft.published is True
    assert saved_draft.published_at is not None


def test_publish_commits_to_github(
    draft_file_fixture: DraftFile,
    post_aggregate_fixture: Post,
    sanitized_html_fixture: str,
    mock_draft_repo: Mock,
    mock_post_repo: Mock,
    mock_markdown_service: Mock,
    mock_html_sanitizer: Mock,
    mock_github_service: Mock,
) -> None:
    """Verify handler commits updated draft to GitHub.

    This test ensures the handler commits the updated draft file to
    GitHub with the correct path and commit message. The commit should
    include the updated front matter with published status.
    """
    mock_draft_repo.find_by_slug.return_value = draft_file_fixture
    mock_post_repo.find_by_slug.return_value = post_aggregate_fixture
    mock_markdown_service.render.return_value = "<p>Raw HTML</p>"
    mock_html_sanitizer.sanitize.return_value = sanitized_html_fixture
    mock_post_repo.save.return_value = post_aggregate_fixture
    mock_github_service.commit_file.return_value = "abc123"

    command = PublishPostCommand(
        slug="test-post", author_id=1, user_role="author"
    )

    publish_post_handler(
        command=command,
        draft_repo=mock_draft_repo,
        post_repo=mock_post_repo,
        markdown_service=mock_markdown_service,
        html_sanitizer=mock_html_sanitizer,
        github_service=mock_github_service,
    )

    mock_github_service.commit_file.assert_called_once()
    commit_call = mock_github_service.commit_file.call_args

    assert commit_call[1]["path"] == "drafts/test-post.md"
    assert "publish" in commit_call[1]["message"].lower()


def test_publish_fails_when_draft_not_found(
    mock_draft_repo: Mock,
    mock_post_repo: Mock,
    mock_markdown_service: Mock,
    mock_html_sanitizer: Mock,
    mock_github_service: Mock,
) -> None:
    """Verify handler raises ValueError when draft doesn't exist.

    This test ensures error handling for missing drafts. If find_by_slug
    returns None, the handler should raise ValueError with a clear message
    indicating the draft was not found. No other services should be called.
    """
    mock_draft_repo.find_by_slug.return_value = None

    mock_post = Mock()
    mock_post.author_id = 1
    mock_post_repo.find_by_slug.return_value = mock_post

    command = PublishPostCommand(
        slug="nonexistent", author_id=1, user_role="author"
    )

    with pytest.raises(ValueError, match="Draft.*not found"):
        publish_post_handler(
            command=command,
            draft_repo=mock_draft_repo,
            post_repo=mock_post_repo,
            markdown_service=mock_markdown_service,
            html_sanitizer=mock_html_sanitizer,
            github_service=mock_github_service,
        )

    mock_draft_repo.find_by_slug.assert_called_once_with("nonexistent")
    mock_markdown_service.render.assert_not_called()
    mock_post_repo.save.assert_not_called()


def test_publish_fails_when_already_published(
    mock_draft_repo: Mock,
    mock_post_repo: Mock,
    mock_markdown_service: Mock,
    mock_html_sanitizer: Mock,
    mock_github_service: Mock,
) -> None:
    """Verify handler raises ValueError when draft already published.

    This test ensures idempotency protection. If the draft's published
    flag is already True, the handler should raise ValueError to prevent
    duplicate publishing operations.
    """
    published_draft = DraftFile(
        slug="already-published",
        title="Published Post",
        author="user123",
        content="Content",
        published=True,
        created_at=datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC),
        published_at=datetime(2025, 1, 15, 14, 30, 0, tzinfo=UTC),
    )
    mock_draft_repo.find_by_slug.return_value = published_draft

    mock_post = Post.create_draft(
        slug="already-published", title="Published Post", author_id=1
    )
    mock_post_repo.find_by_slug.return_value = mock_post

    command = PublishPostCommand(
        slug="already-published", author_id=1, user_role="author"
    )

    with pytest.raises(ValueError, match="already published"):
        publish_post_handler(
            command=command,
            draft_repo=mock_draft_repo,
            post_repo=mock_post_repo,
            markdown_service=mock_markdown_service,
            html_sanitizer=mock_html_sanitizer,
            github_service=mock_github_service,
        )

    mock_markdown_service.render.assert_not_called()
    mock_post_repo.save.assert_not_called()


def test_publish_fails_when_post_not_in_database(
    draft_file_fixture: DraftFile,
    mock_draft_repo: Mock,
    mock_post_repo: Mock,
    mock_markdown_service: Mock,
    mock_html_sanitizer: Mock,
    mock_github_service: Mock,
) -> None:
    """Verify handler raises ValueError when post not found in database.

    This test ensures data integrity. Publishing requires a corresponding
    Post record in the database. If post_repo.find_by_slug() returns None,
    the handler should raise ValueError indicating the post was not found.
    """
    mock_draft_repo.find_by_slug.return_value = draft_file_fixture
    mock_post_repo.find_by_slug.return_value = None

    command = PublishPostCommand(
        slug="test-post", author_id=1, user_role="author"
    )

    with pytest.raises(ValueError, match="Post.*not found.*database"):
        publish_post_handler(
            command=command,
            draft_repo=mock_draft_repo,
            post_repo=mock_post_repo,
            markdown_service=mock_markdown_service,
            html_sanitizer=mock_html_sanitizer,
            github_service=mock_github_service,
        )

    mock_post_repo.save.assert_not_called()


def test_publish_fails_on_database_save_failure(
    draft_file_fixture: DraftFile,
    post_aggregate_fixture: Post,
    sanitized_html_fixture: str,
    mock_draft_repo: Mock,
    mock_post_repo: Mock,
    mock_markdown_service: Mock,
    mock_html_sanitizer: Mock,
    mock_github_service: Mock,
) -> None:
    """Verify handler raises on database save failure.

    This test ensures atomicity. If post_repo.save() raises IntegrityError,
    the handler should propagate the exception without attempting to update
    the draft file or commit to GitHub. Partial failures should not corrupt
    state.
    """
    mock_draft_repo.find_by_slug.return_value = draft_file_fixture
    mock_post_repo.find_by_slug.return_value = post_aggregate_fixture
    mock_markdown_service.render.return_value = "<p>Raw HTML</p>"
    mock_html_sanitizer.sanitize.return_value = sanitized_html_fixture
    mock_post_repo.save.side_effect = IntegrityError(
        "Duplicate key", None, Exception("Duplicate key violation")
    )

    command = PublishPostCommand(
        slug="test-post", author_id=1, user_role="author"
    )

    with pytest.raises(IntegrityError):
        publish_post_handler(
            command=command,
            draft_repo=mock_draft_repo,
            post_repo=mock_post_repo,
            markdown_service=mock_markdown_service,
            html_sanitizer=mock_html_sanitizer,
            github_service=mock_github_service,
        )

    mock_draft_repo.save.assert_not_called()
    mock_github_service.commit_file.assert_not_called()


@patch("backend.application.commands.handlers.publish_post_handler.logger")
def test_publish_continues_when_draft_file_write_fails(
    mock_logger: Mock,
    draft_file_fixture: DraftFile,
    post_aggregate_fixture: Post,
    sanitized_html_fixture: str,
    mock_draft_repo: Mock,
    mock_post_repo: Mock,
    mock_markdown_service: Mock,
    mock_html_sanitizer: Mock,
    mock_github_service: Mock,
) -> None:
    """Verify handler continues when draft file write fails.

    This test ensures resilience to filesystem failures. If draft_repo.save()
    raises OSError, the handler should:
    1. Log a warning about the filesystem failure
    2. Continue execution (not raise exception)
    3. Still attempt GitHub commit (best-effort)

    The post is already published in the database, so the operation is
    considered successful despite draft file failure.
    """
    mock_draft_repo.find_by_slug.return_value = draft_file_fixture
    mock_post_repo.find_by_slug.return_value = post_aggregate_fixture
    mock_markdown_service.render.return_value = "<p>Raw HTML</p>"
    mock_html_sanitizer.sanitize.return_value = sanitized_html_fixture
    mock_post_repo.save.return_value = post_aggregate_fixture
    mock_draft_repo.save.side_effect = OSError("Disk full")
    mock_github_service.commit_file.return_value = "abc123"

    command = PublishPostCommand(
        slug="test-post", author_id=1, user_role="author"
    )

    result = publish_post_handler(
        command=command,
        draft_repo=mock_draft_repo,
        post_repo=mock_post_repo,
        markdown_service=mock_markdown_service,
        html_sanitizer=mock_html_sanitizer,
        github_service=mock_github_service,
    )

    assert result.published is True
    mock_logger.warning.assert_called_once()
    warning_message = mock_logger.warning.call_args[0][0]
    assert (
        "draft" in warning_message.lower() or "file" in warning_message.lower()
    )

    mock_github_service.commit_file.assert_called_once()


@patch("backend.application.commands.handlers.publish_post_handler.logger")
def test_publish_continues_when_github_commit_fails(
    mock_logger: Mock,
    draft_file_fixture: DraftFile,
    post_aggregate_fixture: Post,
    sanitized_html_fixture: str,
    mock_draft_repo: Mock,
    mock_post_repo: Mock,
    mock_markdown_service: Mock,
    mock_html_sanitizer: Mock,
    mock_github_service: Mock,
) -> None:
    """Verify handler continues when GitHub commit fails.

    This test ensures resilience to GitHub API failures. If commit_file()
    returns None (failure), the handler should:
    1. Log a warning about the GitHub failure
    2. Continue execution (not raise exception)
    3. Return successfully published post

    The post is already published in the database, so the operation is
    considered successful despite GitHub failure.
    """
    mock_draft_repo.find_by_slug.return_value = draft_file_fixture
    mock_post_repo.find_by_slug.return_value = post_aggregate_fixture
    mock_markdown_service.render.return_value = "<p>Raw HTML</p>"
    mock_html_sanitizer.sanitize.return_value = sanitized_html_fixture
    mock_post_repo.save.return_value = post_aggregate_fixture
    mock_github_service.commit_file.return_value = None

    command = PublishPostCommand(
        slug="test-post", author_id=1, user_role="author"
    )

    result = publish_post_handler(
        command=command,
        draft_repo=mock_draft_repo,
        post_repo=mock_post_repo,
        markdown_service=mock_markdown_service,
        html_sanitizer=mock_html_sanitizer,
        github_service=mock_github_service,
    )

    assert result.published is True
    mock_logger.warning.assert_called_once()
    warning_message = mock_logger.warning.call_args[0][0]
    assert (
        "github" in warning_message.lower()
        or "commit" in warning_message.lower()
    )


@patch("backend.application.commands.handlers.publish_post_handler.logger")
def test_publish_logs_info_on_success(
    mock_logger: Mock,
    draft_file_fixture: DraftFile,
    post_aggregate_fixture: Post,
    sanitized_html_fixture: str,
    mock_draft_repo: Mock,
    mock_post_repo: Mock,
    mock_markdown_service: Mock,
    mock_html_sanitizer: Mock,
    mock_github_service: Mock,
) -> None:
    """Verify handler logs INFO messages on success.

    This test ensures proper logging for audit trail. The handler should
    log INFO level messages containing:
    - "Publishing post" or similar at start
    - "published to database" or similar on completion
    """
    mock_draft_repo.find_by_slug.return_value = draft_file_fixture
    mock_post_repo.find_by_slug.return_value = post_aggregate_fixture
    mock_markdown_service.render.return_value = "<p>Raw HTML</p>"
    mock_html_sanitizer.sanitize.return_value = sanitized_html_fixture
    mock_post_repo.save.return_value = post_aggregate_fixture
    mock_github_service.commit_file.return_value = "abc123"

    command = PublishPostCommand(
        slug="test-post", author_id=1, user_role="author"
    )

    publish_post_handler(
        command=command,
        draft_repo=mock_draft_repo,
        post_repo=mock_post_repo,
        markdown_service=mock_markdown_service,
        html_sanitizer=mock_html_sanitizer,
        github_service=mock_github_service,
    )

    assert mock_logger.info.call_count >= 1
    info_messages = [call[0][0] for call in mock_logger.info.call_args_list]
    assert any("publish" in msg.lower() for msg in info_messages)


@patch("backend.application.commands.handlers.publish_post_handler.logger")
def test_publish_logs_debug_steps(
    mock_logger: Mock,
    draft_file_fixture: DraftFile,
    post_aggregate_fixture: Post,
    sanitized_html_fixture: str,
    mock_draft_repo: Mock,
    mock_post_repo: Mock,
    mock_markdown_service: Mock,
    mock_html_sanitizer: Mock,
    mock_github_service: Mock,
) -> None:
    """Verify handler logs DEBUG messages for processing steps.

    This test ensures detailed logging for debugging. The handler should
    log DEBUG level messages for:
    - Markdown rendering step
    - HTML sanitization step
    """
    mock_draft_repo.find_by_slug.return_value = draft_file_fixture
    mock_post_repo.find_by_slug.return_value = post_aggregate_fixture
    mock_markdown_service.render.return_value = "<p>Raw HTML</p>"
    mock_html_sanitizer.sanitize.return_value = sanitized_html_fixture
    mock_post_repo.save.return_value = post_aggregate_fixture
    mock_github_service.commit_file.return_value = "abc123"

    command = PublishPostCommand(
        slug="test-post", author_id=1, user_role="author"
    )

    publish_post_handler(
        command=command,
        draft_repo=mock_draft_repo,
        post_repo=mock_post_repo,
        markdown_service=mock_markdown_service,
        html_sanitizer=mock_html_sanitizer,
        github_service=mock_github_service,
    )

    debug_messages = [call[0][0] for call in mock_logger.debug.call_args_list]
    assert any(
        "render" in msg.lower() or "markdown" in msg.lower()
        for msg in debug_messages
    )
    assert any("sanitiz" in msg.lower() for msg in debug_messages)


@patch("backend.application.commands.handlers.publish_post_handler.logger")
def test_publish_logs_warnings_on_partial_failure(
    mock_logger: Mock,
    draft_file_fixture: DraftFile,
    post_aggregate_fixture: Post,
    sanitized_html_fixture: str,
    mock_draft_repo: Mock,
    mock_post_repo: Mock,
    mock_markdown_service: Mock,
    mock_html_sanitizer: Mock,
    mock_github_service: Mock,
) -> None:
    """Verify handler logs WARNING on partial failures.

    This test ensures proper warning logging when best-effort operations
    fail. The handler should log WARNING level messages when:
    - Draft file write fails (OSError)
    - GitHub commit fails (returns None)
    """
    mock_draft_repo.find_by_slug.return_value = draft_file_fixture
    mock_post_repo.find_by_slug.return_value = post_aggregate_fixture
    mock_markdown_service.render.return_value = "<p>Raw HTML</p>"
    mock_html_sanitizer.sanitize.return_value = sanitized_html_fixture
    mock_post_repo.save.return_value = post_aggregate_fixture
    mock_draft_repo.save.side_effect = OSError("Disk full")
    mock_github_service.commit_file.return_value = None

    command = PublishPostCommand(
        slug="test-post", author_id=1, user_role="author"
    )

    publish_post_handler(
        command=command,
        draft_repo=mock_draft_repo,
        post_repo=mock_post_repo,
        markdown_service=mock_markdown_service,
        html_sanitizer=mock_html_sanitizer,
        github_service=mock_github_service,
    )

    assert mock_logger.warning.call_count == 2
    warning_messages = [
        call[0][0] for call in mock_logger.warning.call_args_list
    ]
    assert any(
        "draft" in msg.lower() or "file" in msg.lower()
        for msg in warning_messages
    )
    assert any("github" in msg.lower() for msg in warning_messages)


def test_publish_with_empty_markdown_content(
    post_aggregate_fixture: Post,
    mock_draft_repo: Mock,
    mock_post_repo: Mock,
    mock_markdown_service: Mock,
    mock_html_sanitizer: Mock,
    mock_github_service: Mock,
) -> None:
    """Verify handler publishes draft with empty markdown content.

    This test ensures edge case handling for empty content. A draft with
    empty content string is valid and should be published successfully.
    The rendered and sanitized HTML will be empty, but the operation should
    complete normally.
    """
    empty_draft = DraftFile(
        slug="empty-post",
        title="Empty Post",
        author="user123",
        content="",
        published=False,
        created_at=datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC),
    )
    mock_draft_repo.find_by_slug.return_value = empty_draft
    mock_post_repo.find_by_slug.return_value = post_aggregate_fixture
    mock_markdown_service.render.return_value = ""
    mock_html_sanitizer.sanitize.return_value = ""
    mock_post_repo.save.return_value = post_aggregate_fixture
    mock_github_service.commit_file.return_value = "abc123"

    command = PublishPostCommand(
        slug="empty-post", author_id=1, user_role="author"
    )

    result = publish_post_handler(
        command=command,
        draft_repo=mock_draft_repo,
        post_repo=mock_post_repo,
        markdown_service=mock_markdown_service,
        html_sanitizer=mock_html_sanitizer,
        github_service=mock_github_service,
    )

    mock_markdown_service.render.assert_called_once_with("")
    mock_html_sanitizer.sanitize.assert_called_once_with("")
    assert result.published is True


def test_publish_with_unicode_content(
    post_aggregate_fixture: Post,
    mock_draft_repo: Mock,
    mock_post_repo: Mock,
    mock_markdown_service: Mock,
    mock_html_sanitizer: Mock,
    mock_github_service: Mock,
) -> None:
    """Verify handler correctly processes unicode content.

    This test ensures unicode handling throughout the pipeline. A draft
    with unicode characters (emoji, non-ASCII) should be processed correctly
    through markdown rendering and HTML sanitization without data loss.
    """
    unicode_draft = DraftFile(
        slug="unicode-post",
        title="Unicode Post 🎉",
        author="user123",
        content="# Hello 世界\n\nEmoji test: 🚀 🎨 ✨",
        published=False,
        created_at=datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC),
    )
    mock_draft_repo.find_by_slug.return_value = unicode_draft
    mock_post_repo.find_by_slug.return_value = post_aggregate_fixture
    mock_markdown_service.render.return_value = (
        "<h1>Hello 世界</h1>\n<p>Emoji test: 🚀 🎨 ✨</p>"
    )
    mock_html_sanitizer.sanitize.return_value = (
        "<h1>Hello 世界</h1>\n<p>Emoji test: 🚀 🎨 ✨</p>"
    )
    mock_post_repo.save.return_value = post_aggregate_fixture
    mock_github_service.commit_file.return_value = "abc123"

    command = PublishPostCommand(
        slug="unicode-post", author_id=1, user_role="author"
    )

    result = publish_post_handler(
        command=command,
        draft_repo=mock_draft_repo,
        post_repo=mock_post_repo,
        markdown_service=mock_markdown_service,
        html_sanitizer=mock_html_sanitizer,
        github_service=mock_github_service,
    )

    assert result.published is True
    assert result.html_content is not None
    assert "世界" in result.html_content.value
    assert "🚀" in result.html_content.value


def test_publish_html_content_value_object_created(
    draft_file_fixture: DraftFile,
    post_aggregate_fixture: Post,
    sanitized_html_fixture: str,
    mock_draft_repo: Mock,
    mock_post_repo: Mock,
    mock_markdown_service: Mock,
    mock_html_sanitizer: Mock,
    mock_github_service: Mock,
) -> None:
    """Verify post.html_content is HtmlContent instance, not raw string.

    This test ensures proper domain modeling. The published post's
    html_content property should be an HtmlContent value object, not a
    raw string. This enforces type safety and domain invariants.
    """
    mock_draft_repo.find_by_slug.return_value = draft_file_fixture
    mock_post_repo.find_by_slug.return_value = post_aggregate_fixture
    mock_markdown_service.render.return_value = "<p>Raw HTML</p>"
    mock_html_sanitizer.sanitize.return_value = sanitized_html_fixture
    mock_post_repo.save.return_value = post_aggregate_fixture
    mock_github_service.commit_file.return_value = "abc123"

    command = PublishPostCommand(
        slug="test-post", author_id=1, user_role="author"
    )

    result = publish_post_handler(
        command=command,
        draft_repo=mock_draft_repo,
        post_repo=mock_post_repo,
        markdown_service=mock_markdown_service,
        html_sanitizer=mock_html_sanitizer,
        github_service=mock_github_service,
    )

    assert result.html_content is not None
    assert isinstance(result.html_content, HtmlContent)
    assert result.html_content.value == sanitized_html_fixture
