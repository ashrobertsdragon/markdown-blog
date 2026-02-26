"""Unit tests for Comment aggregate.

This module defines comprehensive tests for the Comment aggregate following
TDD Red phase principles. These tests will initially fail until the Comment
aggregate is implemented.

Test Coverage:
- Factory method tests (12 tests)
- State transition tests (2 tests)
- Serialization tests (5 tests)
- Query method tests (2 tests)
- Unicode/edge case tests (1 test)
"""

import datetime as dt
from datetime import datetime

import pytest

from backend.domain.aggregates.comment import Comment
from backend.domain.value_objects.comment_text import CommentText


def test_create_comment_sets_correct_fields() -> None:
    """Verify factory method initializes all fields.

    Ensures Comment.create() populates post_id, author_id, and text
    with the provided values, and sets safe defaults for parent_id,
    is_deleted, and id so callers never receive uninitialised state.
    """
    comment = Comment.create(post_id=1, author_id=2, text="Hello")

    assert comment.post_id == 1
    assert comment.author_id == 2
    assert str(comment.text) == "Hello"
    assert comment.parent_id is None
    assert comment.is_deleted is False
    assert comment.id is None


def test_create_comment_has_timestamps() -> None:
    """Verify created_at and updated_at set to UTC now.

    Both timestamps must be populated automatically at creation time
    and fall within the bracketed before/after window, satisfying the
    audit trail requirement without relying on caller-supplied values.
    """
    before = datetime.now(dt.UTC)
    comment = Comment.create(post_id=1, author_id=1, text="Hello")
    after = datetime.now(dt.UTC)

    assert before <= comment.created_at <= after
    assert before <= comment.updated_at <= after


def test_create_comment_with_no_parent_id_creates_root_comment() -> None:
    """Verify parent_id defaults to None for top-level comments.

    Top-level comments have no parent. Omitting parent_id from the
    factory call must result in None, not a sentinel value, so callers
    can reliably distinguish root comments from replies.
    """
    comment = Comment.create(post_id=1, author_id=1, text="Hello")

    assert comment.parent_id is None


def test_create_comment_with_parent_id_creates_reply() -> None:
    """Verify parent_id set for replies in flat structure.

    The flat comment structure uses parent_id to model replies without
    nested aggregates. The supplied parent_id must be stored verbatim
    so thread-reconstruction queries can group replies correctly.
    """
    comment = Comment.create(post_id=1, author_id=1, text="Hello", parent_id=5)

    assert comment.parent_id == 5


def test_create_comment_with_empty_text_raises_valueerror() -> None:
    """Verify CommentText validation propagates empty text rejection.

    Empty comment text violates the CommentText invariant. The error
    must surface from Comment.create() so the API layer can return a
    meaningful 400 response without catching domain internals directly.
    """
    with pytest.raises(ValueError):
        Comment.create(post_id=1, author_id=1, text="")


def test_create_comment_with_text_exceeding_5000_chars_raises_valueerror() -> (
    None
):
    """Verify CommentText validation propagates length exceeded rejection.

    Comments longer than 5000 characters exceed the CommentText limit.
    The error must propagate from the value object through the aggregate
    factory so callers see consistent validation behaviour.
    """
    with pytest.raises(ValueError):
        Comment.create(post_id=1, author_id=1, text="a" * 5001)


def test_create_comment_with_invalid_post_id_raises_valueerror() -> None:
    """Verify post_id must be positive integer.

    post_id references a Post aggregate; zero and negative values cannot
    be valid foreign keys. Both boundary cases must raise ValueError with
    a message containing "post_id" so callers can identify the field.
    """
    with pytest.raises(ValueError, match="post_id"):
        Comment.create(post_id=0, author_id=1, text="Hello")

    with pytest.raises(ValueError, match="post_id"):
        Comment.create(post_id=-1, author_id=1, text="Hello")


def test_create_comment_with_invalid_author_id_raises_valueerror() -> None:
    """Verify author_id must be positive integer.

    author_id references a User aggregate; zero and negative values
    cannot be valid foreign keys. Both boundary cases must raise
    ValueError with a message containing "author_id".
    """
    with pytest.raises(ValueError, match="author_id"):
        Comment.create(post_id=1, author_id=0, text="Hello")

    with pytest.raises(ValueError, match="author_id"):
        Comment.create(post_id=1, author_id=-1, text="Hello")


def test_create_comment_with_zero_parent_id_raises_valueerror() -> None:
    """Verify parent_id must be positive if provided.

    A parent_id of zero is not a valid reference. When supplied, parent_id
    must point to an existing comment, so zero must raise ValueError with
    a message containing "parent_id".
    """
    with pytest.raises(ValueError, match="parent_id"):
        Comment.create(post_id=1, author_id=1, text="Hello", parent_id=0)


def test_create_comment_with_negative_parent_id_raises_valueerror() -> None:
    """Verify parent_id must be positive if provided.

    Negative parent_id values cannot reference a real comment. The domain
    must reject them with ValueError containing "parent_id" rather than
    silently storing an invalid reference.
    """
    with pytest.raises(ValueError, match="parent_id"):
        Comment.create(post_id=1, author_id=1, text="Hello", parent_id=-1)


def test_create_comment_wraps_text_in_comment_text_value_object() -> None:
    """Verify text parameter wrapped in CommentText for validation.

    Storing text as a CommentText value object ensures all invariants
    (length, non-empty) are enforced uniformly. The comment.text attribute
    must be an instance of CommentText, not a raw string.
    """
    comment = Comment.create(post_id=1, author_id=1, text="Hello")

    assert isinstance(comment.text, CommentText)


def test_create_comment_initializes_is_deleted_to_false() -> None:
    """Verify soft delete flag starts as False.

    New comments are visible by default. is_deleted must be False at
    creation so readers see all comments unless explicitly moderated,
    and so the soft-delete state transition has a defined starting point.
    """
    comment = Comment.create(post_id=1, author_id=1, text="Hello")

    assert comment.is_deleted is False


def test_comment_cannot_modify_created_at_after_creation() -> None:
    """Verify created_at immutable to preserve audit trail.

    created_at records when the comment was posted and must not be
    alterable after construction. Mutability would undermine the audit
    log and allow timestamp manipulation.
    """
    comment = Comment.create(post_id=1, author_id=1, text="Hello")

    with pytest.raises(AttributeError):
        comment.created_at = datetime.now(dt.UTC)  # type: ignore[misc]


def test_comment_mark_as_deleted_sets_is_deleted_flag() -> None:
    """Verify soft delete marks comment without destroying data.

    mark_as_deleted() must flip is_deleted to True so the comment is
    hidden from public views while its data remains for moderation
    review and thread-integrity purposes.
    """
    comment = Comment.create(post_id=1, author_id=1, text="Hello")

    comment.mark_as_deleted()

    assert comment.is_deleted is True


def test_comment_mark_as_deleted_preserves_text() -> None:
    """Verify soft delete preserves comment text for thread integrity.

    Deleting a comment must not erase its text. Downstream readers may
    render "[deleted]" in place of the content, but the original text
    must remain accessible for moderation and audit purposes.
    """
    original_text = "Hello world"
    comment = Comment.create(post_id=1, author_id=1, text=original_text)

    comment.mark_as_deleted()

    assert str(comment.text) == original_text


def test_comment_to_dict_includes_all_fields() -> None:
    """Verify serialization includes all required API fields.

    The API layer serializes Comment.to_dict() directly into JSON
    responses. All eight fields must be present so clients never
    encounter missing keys regardless of comment state.
    """
    comment = Comment.create(post_id=1, author_id=2, text="Hello")

    result = comment.to_dict()

    assert "id" in result
    assert "post_id" in result
    assert "author_id" in result
    assert "text" in result
    assert "parent_id" in result
    assert "created_at" in result
    assert "updated_at" in result
    assert "is_deleted" in result


def test_comment_to_dict_serializes_text_as_string() -> None:
    """Verify CommentText serialized to plain string.

    JSON cannot represent domain value objects. to_dict() must unwrap
    CommentText to a plain str so the output is directly JSON-serializable
    without further transformation in the API layer.
    """
    comment = Comment.create(post_id=1, author_id=1, text="Hello")

    result = comment.to_dict()

    assert isinstance(result["text"], str)


def test_comment_to_dict_serializes_timestamps_as_iso_format() -> None:
    """Verify timestamps serializable as ISO 8601 strings.

    API clients expect ISO 8601 timestamp strings. to_dict() must convert
    datetime objects to strings containing "T" as the date-time separator,
    ensuring consistent cross-client parsing.
    """
    comment = Comment.create(post_id=1, author_id=1, text="Hello")

    result = comment.to_dict()

    assert isinstance(result["created_at"], str)
    assert "T" in result["created_at"]
    assert isinstance(result["updated_at"], str)
    assert "T" in result["updated_at"]


def test_comment_to_dict_includes_null_parent_id_for_root_comments() -> None:
    """Verify None parent_id preserved in serialization.

    Root comments have no parent. to_dict() must emit null (None) for
    parent_id rather than omitting the key, so API clients can
    distinguish root comments from replies without key-existence checks.
    """
    comment = Comment.create(post_id=1, author_id=1, text="Hello")

    result = comment.to_dict()

    assert result["parent_id"] is None


def test_comment_with_unicode_text_creates_successfully() -> None:
    """Verify unicode comment content supported.

    The platform must accept comments in any language. Unicode text must
    pass through Comment.create() and CommentText without modification,
    enabling a globally accessible comment section.
    """
    comment = Comment.create(post_id=1, author_id=1, text="Unicode 日本語 test")

    assert str(comment.text) == "Unicode 日本語 test"


def test_comment_is_reply_returns_true_when_parent_id_set() -> None:
    """Verify is_reply() identifies replies by parent_id.

    is_reply() provides a semantic predicate so callers can branch on
    comment type without inspecting parent_id directly. A comment with
    any positive parent_id must be classified as a reply.
    """
    comment = Comment.create(post_id=1, author_id=1, text="Hello", parent_id=5)

    assert comment.is_reply() is True


def test_comment_is_reply_returns_false_for_root_comment() -> None:
    """Verify is_reply() returns False for top-level comments.

    Top-level comments have no parent. is_reply() must return False when
    parent_id is None so callers can reliably distinguish thread roots
    from replies using the predicate rather than null-checking parent_id.
    """
    comment = Comment.create(post_id=1, author_id=1, text="Hello")

    assert comment.is_reply() is False
