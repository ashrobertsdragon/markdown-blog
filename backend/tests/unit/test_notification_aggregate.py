"""Unit tests for Notification aggregate."""

import datetime as dt
from datetime import datetime

import pytest

from backend.domain.aggregates.notification import (
    EventType,
    Notification,
    NotificationStatus,
)


def test_create_sets_all_fields_correctly() -> None:
    """Verify Notification.create() initialises all fields to expected values.

    The factory is the sole construction path. All supplied IDs must be stored
    verbatim, status must start as PENDING, attempt_count must be zero, and
    created_at must fall within the before/after bracket captured around the
    call so the timestamp reflects actual creation time.
    """
    before = datetime.now(dt.UTC)
    notification = Notification.create(
        recipient_id=1,
        sender_id=2,
        event_type=EventType.COMMENT_POSTED,
        post_id=3,
        comment_id=4,
    )
    after = datetime.now(dt.UTC)

    assert notification.recipient_id == 1
    assert notification.sender_id == 2
    assert notification.event_type == "comment_posted"
    assert notification.post_id == 3
    assert notification.comment_id == 4
    assert notification.status == NotificationStatus.PENDING
    assert notification.attempt_count == 0
    assert notification.id is None
    assert notification.sent_at is None
    assert notification.error_message is None
    assert before <= notification.created_at <= after


def test_create_raises_on_non_positive_recipient_id() -> None:
    """Verify recipient_id must be a positive integer.

    A recipient_id of zero cannot reference a real User aggregate row.
    The factory must raise ValueError so callers receive a clear rejection
    rather than silently persisting an invalid foreign key reference.
    """
    with pytest.raises(ValueError, match="recipient_id"):
        Notification.create(
            recipient_id=0,
            sender_id=1,
            event_type=EventType.COMMENT_POSTED,
            post_id=1,
            comment_id=1,
        )


def test_create_raises_on_non_positive_sender_id() -> None:
    """Verify sender_id must be a positive integer.

    sender_id identifies the user whose action triggered the notification.
    Zero is not a valid database identifier, so the factory must raise
    ValueError containing "sender_id" to identify the offending field.
    """
    with pytest.raises(ValueError, match="sender_id"):
        Notification.create(
            recipient_id=1,
            sender_id=0,
            event_type=EventType.COMMENT_POSTED,
            post_id=1,
            comment_id=1,
        )


def test_create_raises_on_non_positive_post_id() -> None:
    """Verify post_id must be a positive integer.

    post_id links the notification to a specific Post aggregate. Zero is
    not a valid foreign key, so the factory must raise ValueError with a
    message containing "post_id" to identify the validation failure.
    """
    with pytest.raises(ValueError, match="post_id"):
        Notification.create(
            recipient_id=1,
            sender_id=2,
            event_type=EventType.COMMENT_POSTED,
            post_id=0,
            comment_id=1,
        )


def test_create_raises_on_non_positive_comment_id() -> None:
    """Verify comment_id must be a positive integer.

    comment_id identifies the Comment that triggered the notification. A
    value of zero cannot reference a persisted row, so the factory must
    reject it with ValueError containing "comment_id".
    """
    with pytest.raises(ValueError, match="comment_id"):
        Notification.create(
            recipient_id=1,
            sender_id=2,
            event_type=EventType.COMMENT_POSTED,
            post_id=1,
            comment_id=0,
        )


def test_mark_sent_transitions_status() -> None:
    """Verify mark_sent() sets status to SENT and records the delivery time.

    A notification that has been delivered must transition to SENT. sent_at
    must be populated with a UTC timestamp at the moment of the call so
    downstream auditing and retry logic can determine when delivery occurred.
    """
    notification = Notification.create(
        recipient_id=1,
        sender_id=2,
        event_type=EventType.COMMENT_POSTED,
        post_id=1,
        comment_id=1,
    )
    before = datetime.now(dt.UTC)
    notification.mark_sent("resend-test-id-abc123")
    after = datetime.now(dt.UTC)

    assert notification.status == NotificationStatus.SENT
    assert notification.sent_at is not None
    assert before <= notification.sent_at <= after
    assert notification.resend_email_id == "resend-test-id-abc123"


def test_mark_failed_transitions_status() -> None:
    """Verify mark_failed() sets status to FAILED and records the error.

    When delivery fails the notification must transition to FAILED so the
    retry scheduler can identify it. The error_message must be stored
    verbatim to surface diagnostic information to operators.
    """
    notification = Notification.create(
        recipient_id=1,
        sender_id=2,
        event_type=EventType.COMMENT_POSTED,
        post_id=1,
        comment_id=1,
    )
    notification.mark_failed("SMTP timeout")

    assert notification.status == NotificationStatus.FAILED
    assert notification.error_message == "SMTP timeout"


def test_increment_attempt_increments_count() -> None:
    """Verify increment_attempt() increases attempt_count by exactly one.

    The retry scheduler calls increment_attempt() before each delivery
    attempt. Starting from zero, the first call must yield one so the
    scheduler can enforce a maximum-retry policy.
    """
    notification = Notification.create(
        recipient_id=1,
        sender_id=2,
        event_type=EventType.COMMENT_POSTED,
        post_id=1,
        comment_id=1,
    )
    notification.increment_attempt()

    assert notification.attempt_count == 1


def test_created_at_is_immutable() -> None:
    """Verify created_at cannot be reassigned after construction.

    created_at records the moment the notification was enqueued and must
    not be mutable. Immutability preserves the audit trail and prevents
    callers from backdating records.
    """
    notification = Notification.create(
        recipient_id=1,
        sender_id=2,
        event_type=EventType.COMMENT_POSTED,
        post_id=1,
        comment_id=1,
    )

    with pytest.raises(AttributeError):
        notification.created_at = datetime.now(dt.UTC)


def test_to_dict_serialises_correctly() -> None:
    """Verify to_dict() returns a fully JSON-serializable dict.

    The persistence and API layers consume to_dict() directly. All fields
    must be present, enum values must be plain strings (via .value), and
    all datetime fields must be ISO 8601 strings so no further conversion
    is required before JSON encoding.
    """
    notification = Notification.create(
        recipient_id=1,
        sender_id=2,
        event_type=EventType.REPLY_RECEIVED,
        post_id=3,
        comment_id=4,
    )

    result = notification.to_dict()

    assert "id" in result
    assert "recipient_id" in result
    assert "sender_id" in result
    assert "event_type" in result
    assert "post_id" in result
    assert "comment_id" in result
    assert "status" in result
    assert "attempt_count" in result
    assert "created_at" in result
    assert "sent_at" in result
    assert "has_delivery_error" in result
    assert "error_message" not in result  # excluded to prevent PII leakage

    assert result["status"] == "pending"
    assert isinstance(result["created_at"], str)
    assert "T" in result["created_at"]
    assert result["sent_at"] is None
    assert result["recipient_id"] == 1
    assert result["sender_id"] == 2
    assert result["event_type"] == "reply_received"
    assert result["post_id"] == 3
    assert result["comment_id"] == 4
    assert result["attempt_count"] == 0
    assert result["has_delivery_error"] is False
