"""Unit tests for MentionEvent domain event dataclass.

Covers:
- MentionEvent can be instantiated with valid integer fields
- MentionEvent is immutable (frozen dataclass)
"""

import pytest

from backend.domain.events.mention_event import MentionEvent


class TestMentionEventCreation:
    """Tests for MentionEvent dataclass instantiation."""

    def test_creates_with_valid_fields(self) -> None:
        """MentionEvent stores all four integer fields correctly."""
        event = MentionEvent(
            comment_id=1,
            post_id=2,
            sender_id=3,
            recipient_id=4,
        )
        assert event.comment_id == 1
        assert event.post_id == 2
        assert event.sender_id == 3
        assert event.recipient_id == 4

    def test_fields_are_accessible(self) -> None:
        """All four fields are readable as attributes."""
        event = MentionEvent(
            comment_id=99,
            post_id=88,
            sender_id=77,
            recipient_id=66,
        )
        assert event.comment_id == 99
        assert event.post_id == 88
        assert event.sender_id == 77
        assert event.recipient_id == 66


class TestMentionEventImmutability:
    """Tests for MentionEvent frozen dataclass behaviour."""

    def test_setting_comment_id_raises(self) -> None:
        """Assigning to comment_id after construction raises an error."""
        event = MentionEvent(
            comment_id=1,
            post_id=2,
            sender_id=3,
            recipient_id=4,
        )
        with pytest.raises((AttributeError, TypeError)):
            event.comment_id = 99  # type: ignore[misc]

    def test_setting_recipient_id_raises(self) -> None:
        """Assigning to recipient_id after construction raises an error."""
        event = MentionEvent(
            comment_id=1,
            post_id=2,
            sender_id=3,
            recipient_id=4,
        )
        with pytest.raises((AttributeError, TypeError)):
            event.recipient_id = 42  # type: ignore[misc]

    def test_setting_sender_id_raises(self) -> None:
        """Assigning to sender_id after construction raises an error."""
        event = MentionEvent(
            comment_id=1,
            post_id=2,
            sender_id=3,
            recipient_id=4,
        )
        with pytest.raises((AttributeError, TypeError)):
            event.sender_id = 0  # type: ignore[misc]

    def test_setting_post_id_raises(self) -> None:
        """Assigning to post_id after construction raises an error."""
        event = MentionEvent(
            comment_id=1,
            post_id=2,
            sender_id=3,
            recipient_id=4,
        )
        with pytest.raises((AttributeError, TypeError)):
            event.post_id = 0  # type: ignore[misc]
