"""Unit tests for handle_delete_comment.

Tests authorization (admin soft-delete vs author hard-delete vs rejection),
comment-not-found error, and return value. Repository is mocked.
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


def _comment(*, comment_id: int = 1, author_id: int = 5) -> Comment:
    c = Comment.create(post_id=1, author_id=author_id, text="Hello")
    c.id = comment_id
    return c


def _repo(comment: Comment | None = None) -> Mock:
    repo = Mock(spec=CommentRepository)
    repo.find_by_id.return_value = comment
    repo.hard_delete.return_value = True
    repo.soft_delete.return_value = True
    return repo


def test_author_hard_deletes_own_comment() -> None:
    """Author deleting their own comment triggers hard_delete."""
    comment = _comment(comment_id=1, author_id=5)
    repo = _repo(comment)
    cmd = DeleteCommentCommand(comment_id=1, author_id=5, user_role="author")

    result = handle_delete_comment(cmd, repo)

    repo.hard_delete.assert_called_once_with(1)
    repo.soft_delete.assert_not_called()
    assert result is True


def test_admin_soft_deletes_any_comment() -> None:
    """Admin deleting a comment triggers soft_delete regardless of owner."""
    comment = _comment(comment_id=1, author_id=99)
    repo = _repo(comment)
    cmd = DeleteCommentCommand(comment_id=1, author_id=10, user_role="admin")

    result = handle_delete_comment(cmd, repo)

    repo.soft_delete.assert_called_once_with(1)
    repo.hard_delete.assert_not_called()
    assert result is True


def test_non_owner_non_admin_raises_value_error() -> None:
    """Non-owner, non-admin user cannot delete another user's comment."""
    comment = _comment(comment_id=1, author_id=5)
    repo = _repo(comment)
    cmd = DeleteCommentCommand(comment_id=1, author_id=7, user_role="author")

    with pytest.raises(AuthorizationError, match="Cannot delete another user"):
        handle_delete_comment(cmd, repo)

    repo.hard_delete.assert_not_called()
    repo.soft_delete.assert_not_called()


def test_raises_when_comment_not_found() -> None:
    """ValueError raised when comment does not exist."""
    repo = _repo(None)
    cmd = DeleteCommentCommand(comment_id=999, author_id=1, user_role="admin")

    with pytest.raises(ValueError, match="not found"):
        handle_delete_comment(cmd, repo)
