"""Unit tests for ReplyToCommentCommand."""

import pytest

from backend.application.commands.reply_to_comment_command import (
    ReplyToCommentCommand,
)

_TEXT = "Great point!"
_IP = "127.0.0.1"


def _make(
    *,
    post_id: int = 1,
    parent_comment_id: int = 2,
    author_id: int = 3,
    text: str = _TEXT,
    ip_address: str = _IP,
    is_admin: bool = False,
) -> ReplyToCommentCommand:
    return ReplyToCommentCommand(
        post_id=post_id,
        parent_comment_id=parent_comment_id,
        author_id=author_id,
        text=text,
        ip_address=ip_address,
        is_admin=is_admin,
    )


def test_command_creates_with_valid_fields() -> None:
    """Valid fields produce a command with correct attribute values."""
    cmd = _make()

    assert cmd.post_id == 1
    assert cmd.parent_comment_id == 2
    assert cmd.author_id == 3
    assert cmd.text == _TEXT
    assert cmd.ip_address == _IP
    assert cmd.is_admin is False


def test_command_is_frozen() -> None:
    """Command fields cannot be mutated after construction."""
    cmd = _make()

    with pytest.raises((AttributeError, TypeError)):
        cmd.post_id = 99  # type: ignore[misc]


def test_command_rejects_zero_post_id() -> None:
    """post_id=0 raises ValueError."""
    with pytest.raises(ValueError, match="post_id"):
        _make(post_id=0)


def test_command_rejects_negative_post_id() -> None:
    """Negative post_id raises ValueError."""
    with pytest.raises(ValueError, match="post_id"):
        _make(post_id=-1)


def test_command_rejects_zero_parent_comment_id() -> None:
    """parent_comment_id=0 raises ValueError."""
    with pytest.raises(ValueError, match="parent_comment_id"):
        _make(parent_comment_id=0)


def test_command_rejects_zero_author_id() -> None:
    """author_id=0 raises ValueError."""
    with pytest.raises(ValueError, match="author_id"):
        _make(author_id=0)


def test_command_rejects_empty_text() -> None:
    """Empty text raises ValueError."""
    with pytest.raises(ValueError, match="text"):
        _make(text="")


def test_command_rejects_whitespace_only_text() -> None:
    """Whitespace-only text raises ValueError."""
    with pytest.raises(ValueError, match="text"):
        _make(text="   ")


def test_command_rejects_text_exceeding_5000_chars() -> None:
    """Text longer than 5000 characters raises ValueError."""
    with pytest.raises(ValueError, match="5000"):
        _make(text="x" * 5001)


def test_command_rejects_empty_ip_address() -> None:
    """Empty ip_address raises ValueError."""
    with pytest.raises(ValueError, match="ip_address"):
        _make(ip_address="")


def test_command_equality() -> None:
    """Two commands with identical fields are equal."""
    assert _make() == _make()


def test_command_is_admin_defaults_false() -> None:
    """is_admin defaults to False."""
    assert _make().is_admin is False


def test_command_accepts_is_admin_true() -> None:
    """is_admin=True is accepted."""
    assert _make(is_admin=True).is_admin is True
