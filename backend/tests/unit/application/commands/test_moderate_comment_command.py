"""Unit tests for ModerateCommentCommand."""

import pytest

from backend.application.commands.moderate_comment_command import (
    ModerateCommentCommand,
)


def _make(
    *,
    comment_id: int = 1,
    action: str = "approve",
    moderator_id: int = 10,
    user_role: str = "admin",
) -> ModerateCommentCommand:
    return ModerateCommentCommand(
        comment_id=comment_id,
        action=action,
        moderator_id=moderator_id,
        user_role=user_role,
    )


def test_command_creates_with_valid_fields() -> None:
    """Valid fields produce a command with correct attribute values."""
    cmd = _make()

    assert cmd.comment_id == 1
    assert cmd.action == "approve"
    assert cmd.moderator_id == 10
    assert cmd.user_role == "admin"


def test_command_is_frozen() -> None:
    """Command fields cannot be mutated after construction."""
    cmd = _make()

    with pytest.raises((AttributeError, TypeError)):
        cmd.action = "flag"  # type: ignore[misc]


def test_command_accepts_all_valid_actions() -> None:
    """approve, reject, and flag are all accepted."""
    for action in ("approve", "reject", "flag"):
        cmd = _make(action=action)
        assert cmd.action == action


def test_command_rejects_invalid_action() -> None:
    """Unknown action raises ValueError."""
    with pytest.raises(ValueError, match="action"):
        _make(action="ban")


def test_command_rejects_zero_comment_id() -> None:
    """comment_id=0 raises ValueError."""
    with pytest.raises(ValueError, match="comment_id"):
        _make(comment_id=0)


def test_command_rejects_zero_moderator_id() -> None:
    """moderator_id=0 raises ValueError."""
    with pytest.raises(ValueError, match="moderator_id"):
        _make(moderator_id=0)


def test_command_rejects_empty_user_role() -> None:
    """Empty user_role raises ValueError."""
    with pytest.raises(ValueError, match="user_role"):
        _make(user_role="")


def test_command_equality() -> None:
    """Two commands with identical fields are equal."""
    assert _make() == _make()
