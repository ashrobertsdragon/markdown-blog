"""Unit tests for PublishPostCommand dataclass.

This module defines comprehensive unit tests for the PublishPostCommand
following TDD Red phase principles. These tests will initially fail until
the PublishPostCommand is implemented.

Test Coverage:
- Dataclass structure verification (2 tests)
- Immutability (frozen=True) (1 test)
- String representation for debugging (1 test)

Total: 4 unit tests
"""

import pytest

from backend.application.commands.publish_post_command import PublishPostCommand


def test_command_creation_with_slug() -> None:
    """Verify PublishPostCommand creates successfully with valid slug.

    This test ensures the command dataclass can be instantiated with a
    valid slug value. The slug should be a string and correctly assigned
    to the command instance.
    """
    slug = "my-post"

    command = PublishPostCommand(slug=slug, author_id=1, user_role="author")

    assert command.slug == slug
    assert isinstance(command.slug, str)


def test_command_frozen_dataclass() -> None:
    """Verify PublishPostCommand fields cannot be modified after creation.

    This test ensures the PublishPostCommand is immutable by using frozen
    dataclass. Attempting to modify the slug field after construction should
    raise an error (either AttributeError or TypeError), preventing accidental
    mutation of command objects.
    """
    command = PublishPostCommand(
        slug="frozen-post", author_id=1, user_role="author"
    )

    with pytest.raises((AttributeError, TypeError)):
        command.slug = "modified-slug"


def test_command_slug_type_validation() -> None:
    """Verify PublishPostCommand handles invalid slug types gracefully.

    This test ensures type validation in __post_init__. While type hints
    provide static checking, runtime validation ensures invalid types
    (None, int, etc.) raise clear ValueError messages.
    """
    with pytest.raises((TypeError, ValueError)):
        PublishPostCommand(slug=None, author_id=1, user_role="author")

    with pytest.raises((TypeError, ValueError)):
        PublishPostCommand(slug=123, author_id=1, user_role="author")


def test_command_repr() -> None:
    """Verify PublishPostCommand repr includes slug value for debugging.

    This test ensures the string representation of the command shows the
    slug value, which is useful for debugging and logging. The repr should
    clearly identify the command type and show the slug value.
    """
    command = PublishPostCommand(
        slug="debug-post", author_id=1, user_role="author"
    )

    repr_str = repr(command)

    assert "PublishPostCommand" in repr_str
    assert "debug-post" in repr_str
    assert "slug=" in repr_str.lower() or "slug:" in repr_str.lower()


def test_command_empty_slug_validation() -> None:
    """Verify PublishPostCommand validates empty slug in __post_init__.

    This test ensures the command rejects empty slugs at creation time.
    While Slug value object provides domain validation, the command should
    fail fast with clear error messages for empty strings.
    """
    with pytest.raises(ValueError, match="slug.*empty|slug.*required"):
        PublishPostCommand(slug="", author_id=1, user_role="author")


def test_command_instances_are_comparable() -> None:
    """Verify PublishPostCommand instances can be compared for equality.

    This test ensures dataclass equality works correctly. Two commands
    with identical slug values should be equal, while commands with
    different values should not be equal. This supports testing scenarios
    where commands need to be compared.
    """
    command1 = PublishPostCommand(
        slug="same-post", author_id=1, user_role="author"
    )
    command2 = PublishPostCommand(
        slug="same-post", author_id=1, user_role="author"
    )
    command3 = PublishPostCommand(
        slug="different-post", author_id=1, user_role="author"
    )

    assert command1 == command2
    assert command1 != command3
    assert command2 != command3
