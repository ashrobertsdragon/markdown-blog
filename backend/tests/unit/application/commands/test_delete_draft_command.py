"""Unit tests for DeleteDraftCommand dataclass.

This module defines comprehensive unit tests for the DeleteDraftCommand
following TDD Red phase principles. These tests will initially fail until
the DeleteDraftCommand is implemented.

Test Coverage:
- Command creation with valid slug (1 test)
- Immutability verification (frozen=True) (1 test)
- Type validation (None, int) (1 test)
- Empty slug validation (1 test)
- Slug length validation (1 test)

Total: 5 unit tests
"""

import pytest

from backend.application.commands.delete_draft_command import DeleteDraftCommand


def test_command_creation_with_slug() -> None:
    """Verify DeleteDraftCommand creates successfully with valid slug.

    This test ensures the command dataclass can be instantiated with a
    valid slug value. The slug should be a string and correctly assigned
    to the command instance.
    """
    slug = "my-post"

    command = DeleteDraftCommand(slug=slug, author_id=1, user_role="author")

    assert command.slug == slug
    assert isinstance(command.slug, str)


def test_command_frozen_dataclass() -> None:
    """Verify DeleteDraftCommand fields cannot be modified after creation.

    This test ensures the DeleteDraftCommand is immutable by using frozen
    dataclass. Attempting to modify the slug field after construction should
    raise an error (either AttributeError or TypeError), preventing accidental
    mutation of command objects.
    """
    command = DeleteDraftCommand(
        slug="frozen-post", author_id=1, user_role="author"
    )

    with pytest.raises((AttributeError, TypeError)):
        command.slug = "modified-slug"


def test_command_slug_type_validation() -> None:
    """Verify DeleteDraftCommand handles invalid slug types gracefully.

    This test ensures type validation in __post_init__. While type hints
    provide static checking, runtime validation ensures invalid types
    (None, int, etc.) raise clear ValueError or TypeError messages.
    """
    with pytest.raises((TypeError, ValueError)):
        DeleteDraftCommand(slug=None, author_id=1, user_role="author")

    with pytest.raises((TypeError, ValueError)):
        DeleteDraftCommand(slug=123, author_id=1, user_role="author")


def test_command_empty_slug_validation() -> None:
    """Verify DeleteDraftCommand validates empty slug in __post_init__.

    This test ensures the command rejects empty slugs at creation time.
    While Slug value object provides domain validation, the command should
    fail fast with clear error messages for empty strings.
    """
    with pytest.raises(ValueError, match="slug.*empty|slug.*required"):
        DeleteDraftCommand(slug="", author_id=1, user_role="author")


def test_command_slug_max_length_validation() -> None:
    """Verify DeleteDraftCommand validates slug length.

    This test ensures the command rejects slugs exceeding 1000 characters.
    The command should fail fast with clear error messages for overly
    long slugs.
    """
    long_slug = "a" * 1001

    with pytest.raises(ValueError, match="slug.*long|slug.*length|1000"):
        DeleteDraftCommand(slug=long_slug, author_id=1, user_role="author")
