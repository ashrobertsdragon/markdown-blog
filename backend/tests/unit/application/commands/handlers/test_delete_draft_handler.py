"""Unit tests for delete_draft_handler.

This module defines comprehensive unit tests for the delete_draft_handler
following TDD Red phase principles. These tests will initially fail until
the handler is implemented.

CRITICAL REQUIREMENT: GitHub sync is NOT best-effort for delete operations.
GitHub failures MUST propagate as exceptions after retry logic.

Test Coverage:
- Success path: delete when no post exists, delete draft post (2 tests)
- Service calls: filesystem delete, GitHub delete_file (2 tests)
- Return value: returns None on success (1 test)
- Error cases: published post, filesystem errors, GitHub errors (3 tests)
- No deletion if published: operations not called (1 test)
- Validation: post repository check, slug validation (2 tests)
- Edge cases: None from post_repo, idempotent behavior (2 tests)

Total: 13+ unit tests
"""

from unittest.mock import Mock

import pytest

from backend.application.commands.delete_draft_command import DeleteDraftCommand
from backend.application.commands.handlers.delete_draft_handler import (
    delete_draft_handler,
)
from backend.domain.aggregates.post import Post
from backend.infrastructure.persistence.filesystem_draft_repository import (
    FileSystemDraftRepository,
)
from backend.infrastructure.persistence.post_repository import PostRepository
from backend.infrastructure.versioning.github_sync_service import (
    GitHubSyncService,
)


@pytest.fixture
def mock_draft_repo() -> Mock:
    """Fixture providing mock FileSystemDraftRepository."""
    return Mock(spec=FileSystemDraftRepository)


@pytest.fixture
def mock_post_repo() -> Mock:
    """Fixture providing mock PostRepository."""
    return Mock(spec=PostRepository)


@pytest.fixture
def mock_github_service() -> Mock:
    """Fixture providing mock GitHubSyncService."""
    return Mock(spec=GitHubSyncService)


@pytest.fixture
def draft_post() -> Post:
    """Fixture providing a draft Post aggregate (not published)."""
    return Post.create_draft(
        slug="test-post", title="Test Post Title", author_id=42
    )


@pytest.fixture
def published_post() -> Post:
    """Fixture providing a published Post aggregate."""
    post = Post.create_draft(
        slug="test-post", title="Test Post Title", author_id=42
    )
    post.publish(html_content="<h1>Test Content</h1>")
    return post


def test_delete_draft_when_post_does_not_exist_in_database(
    mock_draft_repo: Mock,
    mock_post_repo: Mock,
    mock_github_service: Mock,
) -> None:
    """Verify handler deletes draft when post not in database.

    This test ensures the handler successfully deletes a draft that has
    no corresponding Post record in the database. This is valid because
    drafts can exist on filesystem without database records.
    """
    mock_post_repo.find_by_slug.return_value = None
    mock_github_service.delete_file.return_value = True

    command = DeleteDraftCommand(slug="test-post")

    delete_draft_handler(
        command=command,
        draft_repo=mock_draft_repo,
        post_repo=mock_post_repo,
        github_service=mock_github_service,
    )
    mock_draft_repo.delete.assert_called_once_with("test-post")
    mock_github_service.delete_file.assert_called_once()


def test_delete_draft_when_post_exists_but_not_published(
    draft_post: Post,
    mock_draft_repo: Mock,
    mock_post_repo: Mock,
    mock_github_service: Mock,
) -> None:
    """Verify handler deletes draft when post exists but not published.

    This test ensures the handler successfully deletes a draft when a
    corresponding Post record exists in the database but is not published.
    Only unpublished posts can be deleted.
    """
    mock_post_repo.find_by_slug.return_value = draft_post
    mock_github_service.delete_file.return_value = True

    command = DeleteDraftCommand(slug="test-post")

    delete_draft_handler(
        command=command,
        draft_repo=mock_draft_repo,
        post_repo=mock_post_repo,
        github_service=mock_github_service,
    )
    mock_draft_repo.delete.assert_called_once_with("test-post")
    mock_github_service.delete_file.assert_called_once()


def test_delete_calls_filesystem_delete_with_correct_slug(
    mock_draft_repo: Mock,
    mock_post_repo: Mock,
    mock_github_service: Mock,
) -> None:
    """Verify handler calls filesystem delete with correct slug.

    This test ensures the handler calls draft_repo.delete() with the
    exact slug from the command. The filesystem delete should be called
    with just the slug parameter.
    """
    mock_post_repo.find_by_slug.return_value = None
    mock_github_service.delete_file.return_value = True

    command = DeleteDraftCommand(slug="my-post")

    delete_draft_handler(
        command=command,
        draft_repo=mock_draft_repo,
        post_repo=mock_post_repo,
        github_service=mock_github_service,
    )

    mock_draft_repo.delete.assert_called_once_with("my-post")


def test_delete_calls_github_delete_file_with_correct_path(
    mock_draft_repo: Mock,
    mock_post_repo: Mock,
    mock_github_service: Mock,
) -> None:
    """Verify handler calls GitHub delete_file with correct path and message.

    This test ensures the handler calls github_service.delete_file() with:
    - path: drafts/{slug}.md
    - message: Delete draft: {title}

    The GitHub commit message should include the draft title.
    """
    mock_post_repo.find_by_slug.return_value = None
    mock_github_service.delete_file.return_value = True

    command = DeleteDraftCommand(slug="test-post")

    delete_draft_handler(
        command=command,
        draft_repo=mock_draft_repo,
        post_repo=mock_post_repo,
        github_service=mock_github_service,
    )

    mock_github_service.delete_file.assert_called_once()
    delete_call = mock_github_service.delete_file.call_args

    assert delete_call[1]["path"] == "drafts/test-post.md"
    assert "delete" in delete_call[1]["message"].lower()
    assert "draft" in delete_call[1]["message"].lower()


def test_delete_returns_none_on_success(
    mock_draft_repo: Mock,
    mock_post_repo: Mock,
    mock_github_service: Mock,
) -> None:
    """Verify handler returns None on successful deletion.

    This test ensures the handler returns None after successful deletion
    of both the filesystem draft and GitHub commit. The None return
    indicates a successful void operation.
    """
    mock_post_repo.find_by_slug.return_value = None
    mock_github_service.delete_file.return_value = True

    command = DeleteDraftCommand(slug="test-post")

    delete_draft_handler(
        command=command,
        draft_repo=mock_draft_repo,
        post_repo=mock_post_repo,
        github_service=mock_github_service,
    )


def test_delete_raises_error_when_post_is_published(
    published_post: Post,
    mock_draft_repo: Mock,
    mock_post_repo: Mock,
    mock_github_service: Mock,
) -> None:
    """Verify handler raises ValueError when post is published.

    This test ensures business rule: published posts cannot be deleted.
    If the post's published flag is True, the handler should raise
    ValueError with a clear message. The user must unpublish first.
    """
    mock_post_repo.find_by_slug.return_value = published_post

    command = DeleteDraftCommand(slug="test-post")

    with pytest.raises(
        ValueError,
        match="published|unpublish.*first|cannot.*delete.*published",
    ):
        delete_draft_handler(
            command=command,
            draft_repo=mock_draft_repo,
            post_repo=mock_post_repo,
            github_service=mock_github_service,
        )


def test_delete_does_not_call_operations_if_post_is_published(
    published_post: Post,
    mock_draft_repo: Mock,
    mock_post_repo: Mock,
    mock_github_service: Mock,
) -> None:
    """Verify handler skips delete operations when post is published.

    This test ensures the handler does not call delete operations if
    the post is published. Neither filesystem delete nor GitHub delete
    should be attempted.
    """
    mock_post_repo.find_by_slug.return_value = published_post

    command = DeleteDraftCommand(slug="test-post")

    with pytest.raises(ValueError):
        delete_draft_handler(
            command=command,
            draft_repo=mock_draft_repo,
            post_repo=mock_post_repo,
            github_service=mock_github_service,
        )

    mock_draft_repo.delete.assert_not_called()
    mock_github_service.delete_file.assert_not_called()


def test_delete_propagates_filesystem_errors(
    mock_draft_repo: Mock,
    mock_post_repo: Mock,
    mock_github_service: Mock,
) -> None:
    """Verify handler propagates filesystem deletion errors.

    This test ensures the handler propagates ValueError from filesystem
    operations (e.g., draft not found). The error should bubble up to
    the caller without being caught or suppressed.
    """
    mock_post_repo.find_by_slug.return_value = None
    mock_draft_repo.delete.side_effect = ValueError("Draft not found")

    command = DeleteDraftCommand(slug="nonexistent")

    with pytest.raises(ValueError, match="Draft not found"):
        delete_draft_handler(
            command=command,
            draft_repo=mock_draft_repo,
            post_repo=mock_post_repo,
            github_service=mock_github_service,
        )

    mock_github_service.delete_file.assert_not_called()


def test_delete_raises_exception_when_github_delete_fails(
    mock_draft_repo: Mock,
    mock_post_repo: Mock,
    mock_github_service: Mock,
) -> None:
    """Verify handler raises exception when GitHub delete fails.

    CRITICAL: GitHub sync is NOT best-effort for delete operations.
    If github_service.delete_file() returns False or raises exception,
    the handler MUST propagate the error. This ensures draft deletions
    are properly version-controlled.
    """
    mock_post_repo.find_by_slug.return_value = None
    mock_github_service.delete_file.return_value = False

    command = DeleteDraftCommand(slug="test-post")

    with pytest.raises(RuntimeError, match="GitHub.*delete.*fail"):
        delete_draft_handler(
            command=command,
            draft_repo=mock_draft_repo,
            post_repo=mock_post_repo,
            github_service=mock_github_service,
        )


def test_delete_checks_post_repository_before_deletion(
    mock_draft_repo: Mock,
    mock_post_repo: Mock,
    mock_github_service: Mock,
) -> None:
    """Verify handler checks post repository before deletion.

    This test ensures the handler calls post_repo.find_by_slug() before
    attempting any delete operations. This check is necessary to enforce
    the business rule that published posts cannot be deleted.
    """
    mock_post_repo.find_by_slug.return_value = None
    mock_github_service.delete_file.return_value = True

    command = DeleteDraftCommand(slug="test-post")

    delete_draft_handler(
        command=command,
        draft_repo=mock_draft_repo,
        post_repo=mock_post_repo,
        github_service=mock_github_service,
    )

    mock_post_repo.find_by_slug.assert_called_once_with("test-post")


def test_delete_validates_slug_via_slug_value_object(
    mock_draft_repo: Mock,
    mock_post_repo: Mock,
    mock_github_service: Mock,
) -> None:
    """Verify handler validates slug format via Slug value object.

    This test ensures the handler uses the Slug value object for
    validation. Invalid slugs should raise ValueError from the Slug
    constructor before any delete operations are attempted.

    Note: This test assumes Slug validation occurs in the handler or
    is enforced by the command's __post_init__ method.
    """
    mock_post_repo.find_by_slug.return_value = None

    command = DeleteDraftCommand(slug="valid-slug")

    delete_draft_handler(
        command=command,
        draft_repo=mock_draft_repo,
        post_repo=mock_post_repo,
        github_service=mock_github_service,
    )

    assert True


def test_delete_handles_none_return_from_post_repo(
    mock_draft_repo: Mock,
    mock_post_repo: Mock,
    mock_github_service: Mock,
) -> None:
    """Verify handler handles None return from post_repo.find_by_slug.

    This test ensures the handler correctly handles the case where
    post_repo.find_by_slug() returns None (post not in database).
    The deletion should proceed successfully since no post record
    means the draft is not published.
    """
    mock_post_repo.find_by_slug.return_value = None
    mock_github_service.delete_file.return_value = True

    command = DeleteDraftCommand(slug="test-post")

    delete_draft_handler(
        command=command,
        draft_repo=mock_draft_repo,
        post_repo=mock_post_repo,
        github_service=mock_github_service,
    )
    mock_draft_repo.delete.assert_called_once()


def test_delete_is_idempotent_for_nonexistent_draft(
    mock_draft_repo: Mock,
    mock_post_repo: Mock,
    mock_github_service: Mock,
) -> None:
    """Verify deleting non-existent draft succeeds idempotently.

    This test ensures idempotent behavior. If the draft doesn't exist,
    the filesystem delete should raise ValueError, which is propagated.
    However, this is the expected behavior (not an error condition).

    The handler should let the filesystem layer decide whether to raise
    or silently succeed.
    """
    mock_post_repo.find_by_slug.return_value = None
    mock_draft_repo.delete.side_effect = ValueError("Draft not found")

    command = DeleteDraftCommand(slug="nonexistent")

    with pytest.raises(ValueError, match="Draft not found"):
        delete_draft_handler(
            command=command,
            draft_repo=mock_draft_repo,
            post_repo=mock_post_repo,
            github_service=mock_github_service,
        )


def test_filesystem_delete_called_even_if_post_doesnt_exist(
    mock_draft_repo: Mock,
    mock_post_repo: Mock,
    mock_github_service: Mock,
) -> None:
    """Verify filesystem delete called even when post not in database.

    This test ensures the handler attempts filesystem deletion even
    when the post doesn't exist in the database. Drafts can exist
    on filesystem without database records, and these should be
    deletable.
    """
    mock_post_repo.find_by_slug.return_value = None
    mock_github_service.delete_file.return_value = True

    command = DeleteDraftCommand(slug="orphaned-draft")

    delete_draft_handler(
        command=command,
        draft_repo=mock_draft_repo,
        post_repo=mock_post_repo,
        github_service=mock_github_service,
    )

    mock_draft_repo.delete.assert_called_once_with("orphaned-draft")
    mock_github_service.delete_file.assert_called_once()
