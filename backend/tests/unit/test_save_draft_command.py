"""Unit tests for SaveDraftCommand dataclass.

This module defines comprehensive unit tests for the SaveDraftCommand
following TDD Red phase principles. These tests will initially fail until
the SaveDraftCommand is implemented.

Test Coverage:
- Dataclass structure verification (2 tests)
- Field validation: slug max 1000 characters (1 test)
- Field validation: content max 10MB (1 test)
- Empty values allowed (2 tests)
- Immutability (frozen=True) (1 test)
- Repr debugging support (1 test)

Total: 8 unit tests
"""

import pytest

from backend.application.commands.save_draft_command import SaveDraftCommand


def test_save_draft_command_creation() -> None:
    """Verify SaveDraftCommand creates successfully with valid fields.

    This test ensures the command dataclass can be instantiated with
    valid slug and content values. Both fields should be strings and
    correctly assigned to the command instance.
    """
    slug = "test-post"
    content = "# Test Post\n\nThis is test content."

    command = SaveDraftCommand(
        slug=slug,
        content=content,
        author_id=1,
        user_role="author",
    )

    assert command.slug == slug
    assert command.content == content


def test_save_draft_command_fields() -> None:
    """Verify SaveDraftCommand has required fields with correct types.

    This test ensures the command dataclass has exactly two required
    fields: slug (str) and content (str). The dataclass must be properly
    defined with type hints for both fields.
    """
    command = SaveDraftCommand(
        slug="my-draft",
        content="Draft content here",
        author_id=1,
        user_role="author",
    )

    assert hasattr(command, "slug")
    assert hasattr(command, "content")
    assert isinstance(command.slug, str)
    assert isinstance(command.content, str)


def test_save_draft_command_immutable() -> None:
    """Verify SaveDraftCommand fields cannot be modified after creation.

    This test ensures the SaveDraftCommand is immutable by using frozen
    dataclass. Attempting to modify fields after construction should raise
    an error (either AttributeError or TypeError), preventing accidental
    mutation of command objects.
    """
    command = SaveDraftCommand(
        slug="frozen-post",
        content="Frozen content",
        author_id=1,
        user_role="author",
    )

    with pytest.raises((AttributeError, TypeError)):
        command.slug = "modified-slug"

    with pytest.raises((AttributeError, TypeError)):
        command.content = "Modified content"


def test_save_draft_command_slug_too_long() -> None:
    """Verify SaveDraftCommand raises ValueError when slug exceeds 1000 chars.

    This test ensures the __post_init__ validation rejects slugs longer
    than 1000 characters. The error message should clearly indicate the
    slug length limit was exceeded.
    """
    long_slug = "a" * 1001
    content = "Valid content"

    with pytest.raises(ValueError) as exc_info:
        SaveDraftCommand(
            slug=long_slug,
            content=content,
            author_id=1,
            user_role="author",
        )

    assert "slug" in str(exc_info.value).lower()
    assert "1000" in str(exc_info.value)


def test_save_draft_command_content_too_long() -> None:
    """Verify SaveDraftCommand raises ValueError when content exceeds 10MB.

    This test ensures the __post_init__ validation rejects content longer
    than 10,000,000 characters (10MB). The error message should clearly
    indicate the content size limit was exceeded.
    """
    slug = "valid-slug"
    large_content = "x" * 10_000_001

    with pytest.raises(ValueError) as exc_info:
        SaveDraftCommand(
            slug=slug,
            content=large_content,
            author_id=1,
            user_role="author",
        )

    assert "content" in str(exc_info.value).lower()
    assert "10" in str(exc_info.value)


def test_save_draft_command_empty_slug_allowed() -> None:
    """Verify SaveDraftCommand allows empty slug.

    This test ensures the command accepts empty slug values at the command
    level. Domain-level validation (via Slug value object) will happen later
    in the handler. The command layer should not reject empty slugs.
    """
    command = SaveDraftCommand(
        slug="",
        content="Some content",
        author_id=1,
        user_role="author",
    )

    assert command.slug == ""


def test_save_draft_command_empty_content_allowed() -> None:
    """Verify SaveDraftCommand allows empty content.

    This test ensures the command accepts empty content values at the
    command level. Domain-level validation will happen later in the handler.
    The command layer should not reject empty content.
    """
    command = SaveDraftCommand(
        slug="valid-slug",
        content="",
        author_id=1,
        user_role="author",
    )

    assert command.content == ""


def test_save_draft_command_repr() -> None:
    """Verify SaveDraftCommand repr includes all field values for debugging.

    This test ensures the string representation of the command shows all
    field values, which is useful for debugging and logging. The repr
    should clearly identify the command type and show both slug and content
    values (or truncated content if too long).
    """
    command = SaveDraftCommand(
        slug="debug-post",
        content="Debug content for testing",
        author_id=1,
        user_role="author",
    )

    repr_str = repr(command)

    assert "SaveDraftCommand" in repr_str
    assert "debug-post" in repr_str
    assert "content=" in repr_str.lower() or "Debug content" in repr_str


def test_save_draft_command_slug_exactly_1000_chars() -> None:
    """Verify SaveDraftCommand allows slug with exactly 1000 characters.

    This test ensures the boundary condition for slug length is correct.
    A slug with exactly 1000 characters should be accepted, while 1001
    should be rejected.
    """
    slug_at_limit = "a" * 1000
    content = "Valid content"

    command = SaveDraftCommand(
        slug=slug_at_limit,
        content=content,
        author_id=1,
        user_role="author",
    )

    assert len(command.slug) == 1000


def test_save_draft_command_content_exactly_10mb() -> None:
    """Verify SaveDraftCommand allows content with exactly 10MB.

    This test ensures the boundary condition for content size is correct.
    Content with exactly 10,000,000 characters should be accepted, while
    10,000,001 should be rejected.
    """
    slug = "boundary-test"
    content_at_limit = "x" * 10_000_000

    command = SaveDraftCommand(
        slug=slug,
        content=content_at_limit,
        author_id=1,
        user_role="author",
    )

    assert len(command.content) == 10_000_000


def test_save_draft_command_instances_are_comparable() -> None:
    """Verify SaveDraftCommand instances can be compared for equality.

    This test ensures dataclass equality works correctly. Two commands
    with identical field values should be equal, while commands with
    different values should not be equal. This supports testing scenarios
    where commands need to be compared.
    """
    command1 = SaveDraftCommand(
        slug="same-post",
        content="Same content",
        author_id=1,
        user_role="author",
    )
    command2 = SaveDraftCommand(
        slug="same-post",
        content="Same content",
        author_id=1,
        user_role="author",
    )
    command3 = SaveDraftCommand(
        slug="different-post",
        content="Different content",
        author_id=1,
        user_role="author",
    )

    assert command1 == command2
    assert command1 != command3
    assert command2 != command3
