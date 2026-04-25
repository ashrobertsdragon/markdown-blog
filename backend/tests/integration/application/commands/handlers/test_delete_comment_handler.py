"""Integration tests for handle_delete_comment handler.

Tests the full handler orchestration using a mock CommentRepository. The
handler is responsible for:
  1. Loading the comment by id (atomic – raises ValueError on failure).
  2. Authorising the request:
     - admin role  → mark_as_deleted() on domain object + save() to repository.
     - own comment → hard_delete (permanent row removal).
     - anything else → raises AuthorizationError.
  3. Calling exactly one of the two deletion paths with the correct id.
  4. Returning True on success.

All infrastructure dependencies are mocked so these tests run without a
database, filesystem, or network.

Test Coverage:
- HappyPath: admin calls save after mark_as_deleted; author hard-deletes; returns True.
- NotFound: find_by_id returns None → ValueError raised; no delete called.
- Authorization: non-owner non-admin raises AuthorizationError; neither delete called.
- RepositoryCalls: correct deletion path is taken; the other method is never called.
- EdgeCases: hard_delete returning False raises ValueError; admin-who-is-author uses admin path.
"""

from unittest.mock import Mock

import pytest

from backend.application.commands.delete_comment_command import (
    DeleteCommentCommand,
)
from backend.application.commands.handlers.delete_comment_handler import (
    handle_delete_comment,
)
from backend.domain.aggregates.comment import Comment
from backend.exceptions import AuthorizationError
from backend.infrastructure.persistence.comment_repository import (
    CommentRepository,
)


def _make_comment(author_id: int = 1, comment_id: int = 10) -> Comment:
    """Build a Comment aggregate for use in tests.

    Returns a Comment with all required fields set, using the factory method
    so domain invariants are respected. The id is patched after creation
    because Comment.create() always sets id=None (pre-persistence state).

    Args:
        author_id: The user who authored the comment.
        comment_id: The database primary key to assign.

    Returns:
        A Comment instance with id set to comment_id.
    """
    comment = Comment.create(post_id=1, author_id=author_id, text="Hello")
    comment.id = comment_id
    return comment


@pytest.fixture()
def comment_repo() -> Mock:
    """Mock CommentRepository with a comment owned by author_id=1.

    Configures the repository methods that the handler may call:
    - find_by_id returns a default comment owned by user 1.
    - save returns the comment unchanged (simulates a successful persist).
    - hard_delete returns True.
    """
    mock = Mock(spec=CommentRepository)
    default_comment = _make_comment(author_id=1, comment_id=10)
    mock.find_by_id.return_value = default_comment
    mock.save.return_value = default_comment
    mock.hard_delete.return_value = True
    return mock


@pytest.fixture()
def admin_command() -> DeleteCommentCommand:
    """Standard delete command issued by an admin user.

    The admin_id (99) does not match the comment's author_id (1), so only the
    role check can grant access — tests that this path selects soft_delete.
    """
    return DeleteCommentCommand(
        comment_id=10,
        author_id=99,
        user_role="admin",
    )


@pytest.fixture()
def author_command() -> DeleteCommentCommand:
    """Delete command issued by the comment's own author (author_id=1).

    The author_id matches the comment fixture's author_id so the handler
    must take the hard-delete path.
    """
    return DeleteCommentCommand(
        comment_id=10,
        author_id=1,
        user_role="author",
    )


class TestDeleteCommentHandlerHappyPath:
    """Tests for the success paths of handle_delete_comment."""

    def test_admin_delete_returns_true(
        self,
        admin_command: DeleteCommentCommand,
        comment_repo: Mock,
    ) -> None:
        """Verify handler returns True when an admin deletes a comment.

        The return value is the signal used by the API layer to confirm
        the operation completed. Returning anything falsy would cause the
        HTTP response to report failure even though the delete succeeded.
        """
        result = handle_delete_comment(
            command=admin_command,
            comment_repository=comment_repo,
        )

        assert result is True

    def test_author_delete_returns_true(
        self,
        author_command: DeleteCommentCommand,
        comment_repo: Mock,
    ) -> None:
        """Verify handler returns True when the comment author deletes their own comment.

        Symmetry with the admin path: both deletion modes must return True so
        callers do not need to distinguish which path was taken to determine
        success.
        """
        result = handle_delete_comment(
            command=author_command,
            comment_repository=comment_repo,
        )

        assert result is True


class TestDeleteCommentHandlerNotFound:
    """Tests for the case where the target comment does not exist."""

    def test_raises_value_error_when_comment_not_found(
        self,
        admin_command: DeleteCommentCommand,
        comment_repo: Mock,
    ) -> None:
        """Verify handler raises ValueError when find_by_id returns None.

        The handler must not attempt to delete a comment that doesn't exist.
        The error message must contain the comment id so callers can map it to
        a meaningful HTTP 404 response without performing a second lookup.
        """
        comment_repo.find_by_id.return_value = None

        with pytest.raises(ValueError, match="10"):
            handle_delete_comment(
                command=admin_command,
                comment_repository=comment_repo,
            )

    def test_soft_delete_not_called_when_comment_not_found(
        self,
        admin_command: DeleteCommentCommand,
        comment_repo: Mock,
    ) -> None:
        """Verify soft_delete is never called when the comment is missing.

        The handler must fail fast after the lookup failure. Attempting a
        soft_delete with a non-existent id could silently succeed (no-op) or
        corrupt unrelated rows, so it must not be called.
        """
        comment_repo.find_by_id.return_value = None

        with pytest.raises(ValueError):
            handle_delete_comment(
                command=admin_command,
                comment_repository=comment_repo,
            )

        comment_repo.soft_delete.assert_not_called()

    def test_hard_delete_not_called_when_comment_not_found(
        self,
        author_command: DeleteCommentCommand,
        comment_repo: Mock,
    ) -> None:
        """Verify hard_delete is never called when the comment is missing.

        Same safety constraint as soft_delete: both deletion methods must be
        skipped when the precondition lookup fails, regardless of user role.
        """
        comment_repo.find_by_id.return_value = None

        with pytest.raises(ValueError):
            handle_delete_comment(
                command=author_command,
                comment_repository=comment_repo,
            )

        comment_repo.hard_delete.assert_not_called()


class TestDeleteCommentHandlerAuthorization:
    """Tests for ownership and role-based authorization invariants."""

    def test_non_owner_non_admin_raises_authorization_error(
        self,
        comment_repo: Mock,
    ) -> None:
        """Verify handler raises AuthorizationError when a stranger attempts deletion.

        A user who neither owns the comment nor holds the admin role must be
        rejected. The error type (AuthorizationError, not ValueError) is
        intentional: it maps to HTTP 403 rather than 404, which correctly
        tells the caller they are forbidden rather than that the resource is
        absent.
        """
        comment_repo.find_by_id.return_value = _make_comment(author_id=1)
        stranger_command = DeleteCommentCommand(
            comment_id=10,
            author_id=42,
            user_role="reader",
        )

        with pytest.raises(AuthorizationError):
            handle_delete_comment(
                command=stranger_command,
                comment_repository=comment_repo,
            )

    def test_authorization_error_message_describes_restriction(
        self,
        comment_repo: Mock,
    ) -> None:
        """Verify AuthorizationError message communicates the specific denial reason.

        A generic "forbidden" message forces callers to guess why they were
        denied. The message must indicate the cross-user deletion constraint so
        API middleware can surface a clear, actionable error to the client.
        """
        comment_repo.find_by_id.return_value = _make_comment(author_id=1)
        stranger_command = DeleteCommentCommand(
            comment_id=10,
            author_id=42,
            user_role="reader",
        )

        with pytest.raises(
            AuthorizationError, match="Cannot delete another user"
        ):
            handle_delete_comment(
                command=stranger_command,
                comment_repository=comment_repo,
            )

    def test_admin_can_delete_another_authors_comment(
        self,
        admin_command: DeleteCommentCommand,
        comment_repo: Mock,
    ) -> None:
        """Verify an admin can delete a comment they do not own.

        Admins must be able to moderate any comment regardless of authorship.
        The admin_command fixture uses author_id=99 while the comment fixture
        uses author_id=1, confirming that the role check overrides ownership.
        """
        comment_repo.find_by_id.return_value = _make_comment(author_id=1)

        result = handle_delete_comment(
            command=admin_command,
            comment_repository=comment_repo,
        )

        assert result is True

    def test_soft_delete_not_called_on_authorization_failure(
        self,
        comment_repo: Mock,
    ) -> None:
        """Verify soft_delete is not called when authorization fails.

        No mutation must occur before the authorization check completes. An
        unauthorized request that silently deletes would be a data integrity
        vulnerability.
        """
        comment_repo.find_by_id.return_value = _make_comment(author_id=1)
        stranger_command = DeleteCommentCommand(
            comment_id=10,
            author_id=42,
            user_role="reader",
        )

        with pytest.raises(AuthorizationError):
            handle_delete_comment(
                command=stranger_command,
                comment_repository=comment_repo,
            )

        comment_repo.soft_delete.assert_not_called()

    def test_hard_delete_not_called_on_authorization_failure(
        self,
        comment_repo: Mock,
    ) -> None:
        """Verify hard_delete is not called when authorization fails.

        Mirrors the soft_delete check: both deletion methods must be guarded
        by authorization so a privilege-escalation attempt through either path
        is blocked.
        """
        comment_repo.find_by_id.return_value = _make_comment(author_id=1)
        stranger_command = DeleteCommentCommand(
            comment_id=10,
            author_id=42,
            user_role="reader",
        )

        with pytest.raises(AuthorizationError):
            handle_delete_comment(
                command=stranger_command,
                comment_repository=comment_repo,
            )

        comment_repo.hard_delete.assert_not_called()


class TestDeleteCommentHandlerRepositoryCalls:
    """Tests verifying that the correct repository method is called with the correct arguments."""

    def test_admin_path_calls_save_with_marked_comment(
        self,
        admin_command: DeleteCommentCommand,
        comment_repo: Mock,
    ) -> None:
        """Verify admin deletion persists the comment via save() with is_deleted=True."""
        handle_delete_comment(
            command=admin_command,
            comment_repository=comment_repo,
        )

        comment_repo.save.assert_called_once()
        saved_comment = comment_repo.save.call_args[0][0]
        assert saved_comment.is_deleted is True

    def test_admin_path_does_not_call_soft_delete_directly(
        self,
        admin_command: DeleteCommentCommand,
        comment_repo: Mock,
    ) -> None:
        """Verify admin deletion does not call soft_delete() on the repository."""
        handle_delete_comment(
            command=admin_command,
            comment_repository=comment_repo,
        )

        comment_repo.soft_delete.assert_not_called()

    def test_admin_path_does_not_call_hard_delete(
        self,
        admin_command: DeleteCommentCommand,
        comment_repo: Mock,
    ) -> None:
        """Verify admin deletion never calls hard_delete."""
        handle_delete_comment(
            command=admin_command,
            comment_repository=comment_repo,
        )

        comment_repo.hard_delete.assert_not_called()

    def test_author_path_calls_hard_delete_with_comment_id(
        self,
        author_command: DeleteCommentCommand,
        comment_repo: Mock,
    ) -> None:
        """Verify author self-deletion calls hard_delete with the correct comment id."""
        handle_delete_comment(
            command=author_command,
            comment_repository=comment_repo,
        )

        comment_repo.hard_delete.assert_called_once_with(10)

    def test_author_path_does_not_call_soft_delete(
        self,
        author_command: DeleteCommentCommand,
        comment_repo: Mock,
    ) -> None:
        """Verify author self-deletion never calls soft_delete."""
        handle_delete_comment(
            command=author_command,
            comment_repository=comment_repo,
        )

        comment_repo.soft_delete.assert_not_called()

    def test_find_by_id_called_with_command_comment_id(
        self,
        admin_command: DeleteCommentCommand,
        comment_repo: Mock,
    ) -> None:
        """Verify the repository lookup uses the comment_id from the command."""
        handle_delete_comment(
            command=admin_command,
            comment_repository=comment_repo,
        )

        comment_repo.find_by_id.assert_called_once_with(10)


class TestDeleteCommentHandlerEdgeCases:
    """Tests for edge cases and race conditions in handle_delete_comment."""

    def test_hard_delete_returning_false_raises_value_error(
        self,
        comment_repo: Mock,
    ) -> None:
        """Verify ValueError is raised when hard_delete signals the row was already gone."""
        comment_repo.find_by_id.return_value = _make_comment(author_id=1)
        comment_repo.hard_delete.return_value = False
        author_command = DeleteCommentCommand(
            comment_id=10, author_id=1, user_role="author"
        )

        with pytest.raises(ValueError, match="10"):
            handle_delete_comment(
                command=author_command,
                comment_repository=comment_repo,
            )

    def test_admin_who_is_also_author_takes_admin_path(
        self,
        comment_repo: Mock,
    ) -> None:
        """Verify admin role takes precedence over author ownership."""
        comment_repo.find_by_id.return_value = _make_comment(author_id=99)
        admin_and_author_command = DeleteCommentCommand(
            comment_id=10, author_id=99, user_role="admin"
        )

        handle_delete_comment(
            command=admin_and_author_command,
            comment_repository=comment_repo,
        )

        comment_repo.save.assert_called_once()
        comment_repo.hard_delete.assert_not_called()
