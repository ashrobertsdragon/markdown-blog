"""Unit tests for CreateNotificationCommand.

Covers:
- Valid instantiation with all positive IDs and known event_type
- Validation rejects non-positive recipient_id, sender_id, post_id, comment_id
- Validation rejects empty or unknown event_type strings
- Known event types: comment_posted, reply_received, mention
- Frozen dataclass prevents mutation
"""

import pytest
from backend.application.commands.create_notification_command import (
    CreateNotificationCommand,
)


def _make(
    *,
    recipient_id: int = 1,
    sender_id: int = 2,
    post_id: int = 10,
    comment_id: int = 5,
    event_type: str = "comment_posted",
) -> CreateNotificationCommand:
    """Build a valid CreateNotificationCommand for test use."""
    return CreateNotificationCommand(
        recipient_id=recipient_id,
        sender_id=sender_id,
        post_id=post_id,
        comment_id=comment_id,
        event_type=event_type,
    )


def test_valid_command_instantiates() -> None:
    """Valid fields produce a command without raising."""
    cmd = _make()

    assert cmd.recipient_id == 1
    assert cmd.sender_id == 2
    assert cmd.post_id == 10
    assert cmd.comment_id == 5
    assert cmd.event_type == "comment_posted"


def test_accepts_reply_received_event_type() -> None:
    """reply_received is a known event_type and does not raise."""
    cmd = _make(event_type="reply_received")

    assert cmd.event_type == "reply_received"


def test_accepts_mention_event_type() -> None:
    """mention is a known event_type and does not raise."""
    cmd = _make(event_type="mention")

    assert cmd.event_type == "mention"


def test_rejects_zero_recipient_id() -> None:
    """recipient_id=0 raises ValueError."""
    with pytest.raises(ValueError, match="recipient_id"):
        _make(recipient_id=0)


def test_rejects_negative_recipient_id() -> None:
    """Negative recipient_id raises ValueError."""
    with pytest.raises(ValueError, match="recipient_id"):
        _make(recipient_id=-5)


def test_rejects_zero_sender_id() -> None:
    """sender_id=0 raises ValueError."""
    with pytest.raises(ValueError, match="sender_id"):
        _make(sender_id=0)


def test_rejects_negative_sender_id() -> None:
    """Negative sender_id raises ValueError."""
    with pytest.raises(ValueError, match="sender_id"):
        _make(sender_id=-1)


def test_rejects_zero_post_id() -> None:
    """post_id=0 raises ValueError."""
    with pytest.raises(ValueError, match="post_id"):
        _make(post_id=0)


def test_rejects_negative_post_id() -> None:
    """Negative post_id raises ValueError."""
    with pytest.raises(ValueError, match="post_id"):
        _make(post_id=-10)


def test_rejects_zero_comment_id() -> None:
    """comment_id=0 raises ValueError."""
    with pytest.raises(ValueError, match="comment_id"):
        _make(comment_id=0)


def test_rejects_negative_comment_id() -> None:
    """Negative comment_id raises ValueError."""
    with pytest.raises(ValueError, match="comment_id"):
        _make(comment_id=-3)


def test_rejects_empty_event_type() -> None:
    """Empty string event_type raises ValueError."""
    with pytest.raises(ValueError, match="event_type"):
        _make(event_type="")


def test_rejects_unknown_event_type() -> None:
    """Unknown event_type string raises ValueError."""
    with pytest.raises(ValueError, match="event_type"):
        _make(event_type="bogus")


def test_rejects_whitespace_only_event_type() -> None:
    """Whitespace-only event_type raises ValueError."""
    with pytest.raises(ValueError, match="event_type"):
        _make(event_type="   ")


def test_command_is_frozen() -> None:
    """Frozen dataclass prevents attribute mutation."""
    cmd = _make()

    with pytest.raises((AttributeError, TypeError)):
        cmd.recipient_id = 99
