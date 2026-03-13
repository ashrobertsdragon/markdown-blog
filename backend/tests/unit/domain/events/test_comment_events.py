"""Unit tests for CommentPostedEvent and ReplyReceivedEvent domain events.

Covers:
- Field presence and type correctness for both event dataclasses
- Frozen (immutable) enforcement
- Equality semantics — two events with identical fields compare equal
- Events with different field values compare not equal
- Hash stability (frozen dataclasses must be hashable)
"""

import pytest

from backend.domain.events.comment_posted import CommentPostedEvent
from backend.domain.events.reply_received import ReplyReceivedEvent


class TestCommentPostedEvent:
    """Tests for CommentPostedEvent frozen dataclass."""

    def test_fields_are_stored_correctly(self) -> None:
        """Constructor args are accessible as attributes with correct values."""
        event = CommentPostedEvent(
            comment_id=1, post_id=2, sender_id=3, recipient_id=4
        )
        assert event.comment_id == 1
        assert event.post_id == 2
        assert event.sender_id == 3
        assert event.recipient_id == 4

    def test_is_immutable(self) -> None:
        """Frozen dataclass raises FrozenInstanceError on attribute mutation."""
        event = CommentPostedEvent(
            comment_id=1, post_id=2, sender_id=3, recipient_id=4
        )
        with pytest.raises(Exception):
            event.comment_id = 99  # type: ignore[misc]

    def test_equal_instances_compare_equal(self) -> None:
        """Two events with identical fields are equal."""
        a = CommentPostedEvent(
            comment_id=5, post_id=10, sender_id=20, recipient_id=30
        )
        b = CommentPostedEvent(
            comment_id=5, post_id=10, sender_id=20, recipient_id=30
        )
        assert a == b

    def test_different_comment_id_not_equal(self) -> None:
        """Events with different comment_id are not equal."""
        a = CommentPostedEvent(
            comment_id=1, post_id=2, sender_id=3, recipient_id=4
        )
        b = CommentPostedEvent(
            comment_id=99, post_id=2, sender_id=3, recipient_id=4
        )
        assert a != b

    def test_is_hashable(self) -> None:
        """Frozen dataclass instances can be used as set members."""
        event = CommentPostedEvent(
            comment_id=1, post_id=2, sender_id=3, recipient_id=4
        )
        assert hash(event) == hash(event)
        s = {event}
        assert event in s

    def test_all_fields_are_integers(self) -> None:
        """All event fields hold integer values, not strings or None."""
        event = CommentPostedEvent(
            comment_id=7, post_id=8, sender_id=9, recipient_id=10
        )
        assert isinstance(event.comment_id, int)
        assert isinstance(event.post_id, int)
        assert isinstance(event.sender_id, int)
        assert isinstance(event.recipient_id, int)


class TestReplyReceivedEvent:
    """Tests for ReplyReceivedEvent frozen dataclass."""

    def test_fields_are_stored_correctly(self) -> None:
        """Constructor args are accessible as attributes with correct values."""
        event = ReplyReceivedEvent(
            comment_id=11, post_id=22, sender_id=33, recipient_id=44
        )
        assert event.comment_id == 11
        assert event.post_id == 22
        assert event.sender_id == 33
        assert event.recipient_id == 44

    def test_is_immutable(self) -> None:
        """Frozen dataclass raises FrozenInstanceError on attribute mutation."""
        event = ReplyReceivedEvent(
            comment_id=11, post_id=22, sender_id=33, recipient_id=44
        )
        with pytest.raises(Exception):
            event.recipient_id = 99  # type: ignore[misc]

    def test_equal_instances_compare_equal(self) -> None:
        """Two events with identical fields are equal."""
        a = ReplyReceivedEvent(
            comment_id=5, post_id=10, sender_id=20, recipient_id=30
        )
        b = ReplyReceivedEvent(
            comment_id=5, post_id=10, sender_id=20, recipient_id=30
        )
        assert a == b

    def test_different_sender_id_not_equal(self) -> None:
        """Events with different sender_id are not equal."""
        a = ReplyReceivedEvent(
            comment_id=1, post_id=2, sender_id=3, recipient_id=4
        )
        b = ReplyReceivedEvent(
            comment_id=1, post_id=2, sender_id=99, recipient_id=4
        )
        assert a != b

    def test_is_hashable(self) -> None:
        """Frozen dataclass instances can be placed in sets."""
        event = ReplyReceivedEvent(
            comment_id=11, post_id=22, sender_id=33, recipient_id=44
        )
        assert hash(event) == hash(event)
        s = {event}
        assert event in s

    def test_all_fields_are_integers(self) -> None:
        """All event fields hold integer values."""
        event = ReplyReceivedEvent(
            comment_id=11, post_id=22, sender_id=33, recipient_id=44
        )
        assert isinstance(event.comment_id, int)
        assert isinstance(event.post_id, int)
        assert isinstance(event.sender_id, int)
        assert isinstance(event.recipient_id, int)

    def test_comment_posted_and_reply_received_are_distinct_types(self) -> None:
        """CommentPostedEvent and ReplyReceivedEvent differ despite same fields.

        Different types must not compare equal even when all four integer
        fields carry identical values.
        """
        posted = CommentPostedEvent(
            comment_id=1, post_id=2, sender_id=3, recipient_id=4
        )
        replied = ReplyReceivedEvent(
            comment_id=1, post_id=2, sender_id=3, recipient_id=4
        )
        assert posted != replied
