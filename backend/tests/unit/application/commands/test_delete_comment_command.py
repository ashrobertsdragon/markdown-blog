"""Unit tests for DeleteCommentCommand."""

import pytest

from backend.application.commands.delete_comment_command import (
    DeleteCommentCommand,
)


def _make(
    *,
    comment_id: int = 1,
    author_id: int = 2,
    user_role: str = "author",
) -> DeleteCommentCommand:
    return DeleteCommentCommand(
        comment_id=comment_id,
        author_id=author_id,
        user_role=user_role,
    )


def test_command_creates_with_valid_fields() -> None:
    """Valid fields produce a command with correct attribute values."""
    cmd = _make()

    assert cmd.comment_id == 1
    assert cmd.author_id == 2
    assert cmd.user_role == "author"


def test_command_is_frozen() -> None:
    """Command fields cannot be mutated after construction."""
    cmd = _make()

    with pytest.raises((AttributeError, TypeError)):
        cmd.comment_id = 99  # type: ignore[misc]


def test_command_rejects_zero_comment_id() -> None:
    """comment_id=0 raises ValueError."""
    with pytest.raises(ValueError, match="comment_id"):
        _make(comment_id=0)


def test_command_rejects_negative_comment_id() -> None:
    """Negative comment_id raises ValueError."""
    with pytest.raises(ValueError, match="comment_id"):
        _make(comment_id=-5)


def test_command_rejects_zero_author_id() -> None:
    """author_id=0 raises ValueError."""
    with pytest.raises(ValueError, match="author_id"):
        _make(author_id=0)


def test_command_rejects_empty_user_role() -> None:
    """Empty user_role raises ValueError."""
    with pytest.raises(ValueError, match="user_role"):
        _make(user_role="")


def test_command_accepts_admin_role() -> None:
    """user_role='admin' is a valid value."""
    cmd = _make(user_role="admin")

    assert cmd.user_role == "admin"


def test_command_equality() -> None:
    """Two commands with identical fields are equal."""
    assert _make() == _make()
