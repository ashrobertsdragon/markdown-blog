"""Unit tests for handle_moderate_comment.

Tests admin-only authorization, all three moderation actions, comment-not-found
error, and return values. Repository is mocked.
"""

from unittest.mock import Mock

import pytest

from backend.application.commands.handlers.moderate_comment_handler import (
    handle_moderate_comment,
)
from backend.application.commands.moderate_comment_command import (
    ModerateCommentCommand,
)
from backend.domain.aggregates.comment import Comment
from backend.infrastructure.persistence.comment_repository import (
    CommentRepository,
)


def _comment(*, pending: bool = True) -> Comment:
    c = Comment.create(post_id=1, author_id=5, text="Some comment")
    c.id = 1
    if pending:
        c.mark_as_pending_moderation()
    return c


def _repo(comment: Comment | None = None) -> Mock:
    repo = Mock(spec=CommentRepository)
    repo.find_by_id.return_value = comment
    repo.save.side_effect = lambda c: c
    repo.hard_delete.return_value = True
    return repo


def _cmd(action: str, *, user_role: str = "admin") -> ModerateCommentCommand:
    return ModerateCommentCommand(
        comment_id=1,
        action=action,
        moderator_id=10,
        user_role=user_role,
    )


def test_approve_clears_pending_flag_and_saves() -> None:
    """Approve clears is_pending_moderation and calls repository.save."""
    comment = _comment(pending=True)
    repo = _repo(comment)

    result = handle_moderate_comment(_cmd("approve"), repo)

    assert result is not None
    assert result.is_pending_moderation is False
    repo.save.assert_called_once()
    repo.hard_delete.assert_not_called()


def test_reject_soft_deletes_and_saves() -> None:
    """Reject marks comment as deleted and saves it."""
    comment = _comment()
    repo = _repo(comment)

    result = handle_moderate_comment(_cmd("reject"), repo)

    assert result is not None
    assert result.is_deleted is True
    repo.save.assert_called_once()
    repo.hard_delete.assert_not_called()


def test_flag_sets_pending_and_saves() -> None:
    """Flag sets is_pending_moderation and calls repository.save."""
    comment = _comment(pending=False)
    repo = _repo(comment)

    result = handle_moderate_comment(_cmd("flag"), repo)

    assert result is not None
    assert result.is_pending_moderation is True
    repo.save.assert_called_once()


def test_non_admin_raises_value_error() -> None:
    """Non-admin user attempting moderation raises ValueError."""
    repo = _repo(_comment())

    with pytest.raises(ValueError, match="admin"):
        handle_moderate_comment(_cmd("approve", user_role="author"), repo)

    repo.save.assert_not_called()
    repo.hard_delete.assert_not_called()


def test_raises_when_comment_not_found() -> None:
    """ValueError raised when comment does not exist."""
    repo = _repo(None)

    with pytest.raises(ValueError, match="not found"):
        handle_moderate_comment(_cmd("approve"), repo)
