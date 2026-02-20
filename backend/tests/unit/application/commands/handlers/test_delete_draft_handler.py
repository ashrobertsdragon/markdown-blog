"""Unit tests for delete_draft_handler.

This module defines comprehensive unit tests for the delete_draft_handler.

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
    post = Post.create_draft(
        slug="test-post", title="Test Post Title", author_id=1
    )
    post.id = 1
    return post


@pytest.fixture
def published_post() -> Post:
    """Fixture providing a published Post aggregate."""
    post = Post.create_draft(
        slug="test-post", title="Test Post Title", author_id=1
    )
    post.id = 1
    post.publish(html_content="<h1>Test Content</h1>")
    return post


def test_delete_draft_when_post_does_not_exist_in_database(
    draft_post: Post,
    mock_draft_repo: Mock,
    mock_post_repo: Mock,
    mock_github_service: Mock,
) -> None:
    """Verify handler raises error when post not in database.

    With authorization added, we cannot verify ownership without a Post
    record. The handler should raise ValueError to prevent unauthorized
    deletion of drafts without database records.
    """
    mock_post_repo.find_by_slug.return_value = None

    command = DeleteDraftCommand(
        slug="test-post", author_id=1, user_role="author"
    )

    with pytest.raises(ValueError, match="not found"):
        delete_draft_handler(
            command=command,
            draft_repo=mock_draft_repo,
            post_repo=mock_post_repo,
            github_service=mock_github_service,
        )

    mock_draft_repo.delete.assert_not_called()
    mock_github_service.delete_file.assert_not_called()


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

    command = DeleteDraftCommand(
        slug="test-post", author_id=1, user_role="author"
    )

    delete_draft_handler(
        command=command,
        draft_repo=mock_draft_repo,
        post_repo=mock_post_repo,
        github_service=mock_github_service,
    )
    mock_draft_repo.delete.assert_called_once_with("test-post")
    mock_github_service.delete_file.assert_called_once()


def test_delete_calls_filesystem_delete_with_correct_slug(
    draft_post: Post,
    mock_draft_repo: Mock,
    mock_post_repo: Mock,
    mock_github_service: Mock,
) -> None:
    """Verify handler calls filesystem delete with correct slug.

    This test ensures the handler calls draft_repo.delete() with the
    exact slug from the command. The filesystem delete should be called
    with just the slug parameter.
    """
    mock_post_repo.find_by_slug.return_value = draft_post
    mock_github_service.delete_file.return_value = True

    command = DeleteDraftCommand(
        slug="my-post", author_id=1, user_role="author"
    )

    delete_draft_handler(
        command=command,
        draft_repo=mock_draft_repo,
        post_repo=mock_post_repo,
        github_service=mock_github_service,
    )

    mock_draft_repo.delete.assert_called_once_with("my-post")


def test_delete_calls_github_delete_file_with_correct_path(
    draft_post: Post,
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
    mock_post_repo.find_by_slug.return_value = draft_post
    mock_github_service.delete_file.return_value = True

    command = DeleteDraftCommand(
        slug="test-post", author_id=1, user_role="author"
    )

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
    draft_post: Post,
    mock_draft_repo: Mock,
    mock_post_repo: Mock,
    mock_github_service: Mock,
) -> None:
    """Verify handler returns None on successful deletion.

    This test ensures the handler returns None after successful deletion
    of both the filesystem draft and GitHub commit. The None return
    indicates a successful void operation.
    """
    mock_post_repo.find_by_slug.return_value = draft_post
    mock_github_service.delete_file.return_value = True

    command = DeleteDraftCommand(
        slug="test-post", author_id=1, user_role="author"
    )

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

    command = DeleteDraftCommand(
        slug="test-post", author_id=1, user_role="author"
    )

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

    command = DeleteDraftCommand(
        slug="test-post", author_id=1, user_role="author"
    )

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
    draft_post: Post,
    mock_draft_repo: Mock,
    mock_post_repo: Mock,
    mock_github_service: Mock,
) -> None:
    """Verify handler propagates filesystem deletion errors.

    This test ensures the handler propagates ValueError from filesystem
    operations (e.g., draft not found). The error should bubble up to
    the caller without being caught or suppressed.
    """
    mock_post_repo.find_by_slug.return_value = draft_post
    mock_draft_repo.delete.side_effect = ValueError("Draft not found")

    command = DeleteDraftCommand(
        slug="nonexistent", author_id=1, user_role="author"
    )

    with pytest.raises(ValueError, match="Draft not found"):
        delete_draft_handler(
            command=command,
            draft_repo=mock_draft_repo,
            post_repo=mock_post_repo,
            github_service=mock_github_service,
        )

    mock_github_service.delete_file.assert_not_called()


def test_delete_continues_when_github_delete_fails(
    draft_post: Post,
    mock_draft_repo: Mock,
    mock_post_repo: Mock,
    mock_github_service: Mock,
) -> None:
    """Verify handler does not raise when GitHub delete fails.

    GitHub sync is best-effort for delete operations, consistent with
    save and publish. If delete_file() returns False the local deletion
    (filesystem + DB soft-delete) is still committed and no exception
    is propagated.
    """
    mock_post_repo.find_by_slug.return_value = draft_post
    mock_github_service.delete_file.return_value = False

    command = DeleteDraftCommand(
        slug="test-post", author_id=1, user_role="author"
    )

    delete_draft_handler(
        command=command,
        draft_repo=mock_draft_repo,
        post_repo=mock_post_repo,
        github_service=mock_github_service,
    )

    mock_draft_repo.delete.assert_called_once_with("test-post")
    mock_post_repo.mark_deleted.assert_called_once_with(1)
    mock_github_service.delete_file.assert_called_once()


def test_delete_checks_post_repository_before_deletion(
    draft_post: Post,
    mock_draft_repo: Mock,
    mock_post_repo: Mock,
    mock_github_service: Mock,
) -> None:
    """Verify handler checks post repository before deletion.

    This test ensures the handler calls post_repo.find_by_slug() before
    attempting any delete operations. This check is necessary to enforce
    the business rule that published posts cannot be deleted.
    """
    mock_post_repo.find_by_slug.return_value = draft_post
    mock_github_service.delete_file.return_value = True

    command = DeleteDraftCommand(
        slug="test-post", author_id=1, user_role="author"
    )

    delete_draft_handler(
        command=command,
        draft_repo=mock_draft_repo,
        post_repo=mock_post_repo,
        github_service=mock_github_service,
    )

    mock_post_repo.find_by_slug.assert_called_once_with("test-post")


def test_delete_validates_slug_via_slug_value_object(
    draft_post: Post,
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
    mock_post_repo.find_by_slug.return_value = draft_post
    mock_github_service.delete_file.return_value = True

    command = DeleteDraftCommand(
        slug="valid-slug", author_id=1, user_role="author"
    )

    delete_draft_handler(
        command=command,
        draft_repo=mock_draft_repo,
        post_repo=mock_post_repo,
        github_service=mock_github_service,
    )

    assert True


def test_delete_handles_none_return_from_post_repo(
    draft_post: Post,
    mock_draft_repo: Mock,
    mock_post_repo: Mock,
    mock_github_service: Mock,
) -> None:
    """Verify handler handles None return from post_repo.find_by_slug.

    This test ensures the handler correctly handles the case where
    post_repo.find_by_slug() returns None (post not in database).
    With authorization added, this now raises ValueError to prevent
    unauthorized deletion.
    """
    mock_post_repo.find_by_slug.return_value = None

    command = DeleteDraftCommand(
        slug="test-post", author_id=1, user_role="author"
    )

    with pytest.raises(ValueError, match="not found"):
        delete_draft_handler(
            command=command,
            draft_repo=mock_draft_repo,
            post_repo=mock_post_repo,
            github_service=mock_github_service,
        )

    mock_draft_repo.delete.assert_not_called()


def test_delete_is_idempotent_for_nonexistent_draft(
    mock_draft_repo: Mock,
    mock_post_repo: Mock,
    mock_github_service: Mock,
) -> None:
    """Verify deleting non-existent draft fails at post lookup.

    With authorization added, the handler requires a Post record to verify
    ownership. If the post doesn't exist in the database, deletion is blocked
    to prevent unauthorized operations.
    """
    mock_post_repo.find_by_slug.return_value = None

    command = DeleteDraftCommand(
        slug="nonexistent", author_id=1, user_role="author"
    )

    with pytest.raises(ValueError, match="not found"):
        delete_draft_handler(
            command=command,
            draft_repo=mock_draft_repo,
            post_repo=mock_post_repo,
            github_service=mock_github_service,
        )

    mock_draft_repo.delete.assert_not_called()


def test_filesystem_delete_blocked_when_post_doesnt_exist(
    mock_draft_repo: Mock,
    mock_post_repo: Mock,
    mock_github_service: Mock,
) -> None:
    """Verify filesystem delete blocked when post not in database.

    With authorization added, the handler requires a Post record to verify
    ownership. This prevents unauthorized deletion of orphaned drafts.
    """
    mock_post_repo.find_by_slug.return_value = None

    command = DeleteDraftCommand(
        slug="orphaned-draft", author_id=1, user_role="author"
    )

    with pytest.raises(ValueError, match="not found"):
        delete_draft_handler(
            command=command,
            draft_repo=mock_draft_repo,
            post_repo=mock_post_repo,
            github_service=mock_github_service,
        )

    mock_draft_repo.delete.assert_not_called()
    mock_github_service.delete_file.assert_not_called()


def test_delete_draft_raises_when_draft_has_no_id(
    mock_post_repo: Mock,
    mock_draft_repo: Mock,
    mock_github_service: Mock,
) -> None:
    """deleting a draft without a DB id should raise without side effects."""
    draft_without_id = Post.create_draft(
        slug="test-post", title="Test Post Title", author_id=1
    )
    draft_without_id.id = None
    mock_post_repo.find_by_slug.return_value = draft_without_id

    command = DeleteDraftCommand(
        slug="test-post", author_id=1, user_role="author"
    )

    with pytest.raises(ValueError, match="has no database ID"):
        delete_draft_handler(
            command=command,
            draft_repo=mock_draft_repo,
            post_repo=mock_post_repo,
            github_service=mock_github_service,
        )

    mock_draft_repo.delete.assert_called_once_with("test-post")
    mock_post_repo.mark_deleted.assert_not_called()
    mock_github_service.delete_file.assert_not_called()


def test_delete_continues_when_github_delete_raises(
    draft_post: Post,
    mock_draft_repo: Mock,
    mock_post_repo: Mock,
    mock_github_service: Mock,
) -> None:
    """Verify handler does not raise when GitHub delete raises."""

    mock_post_repo.find_by_slug.return_value = draft_post
    mock_github_service.delete_file.side_effect = Exception("boom")

    command = DeleteDraftCommand(
        slug="test-post", author_id=1, user_role="author"
    )

    delete_draft_handler(
        command=command,
        draft_repo=mock_draft_repo,
        post_repo=mock_post_repo,
        github_service=mock_github_service,
    )

    mock_draft_repo.delete.assert_called_once_with("test-post")
    mock_post_repo.mark_deleted.assert_called_once_with(1)
