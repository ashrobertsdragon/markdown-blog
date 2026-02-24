"""Unit tests for CreateDraftCommand dataclass.

This module defines comprehensive unit tests for the CreateDraftCommand
following TDD Red phase principles. These tests will initially fail until
the CreateDraftCommand is implemented.

Test Coverage:
- Dataclass structure verification (2 tests)
- Field type validation (1 test)
- Value assignment correctness (1 test)

Total: 4 unit tests
"""

import pytest

from backend.application.commands.create_draft_command import (
    CreateDraftCommand,
)


def test_command_dataclass_structure() -> None:
    """Verify CreateDraftCommand has required fields with correct types.

    This test ensures the command dataclass has exactly three required
    fields: slug (str), title (str), and author_id (int). The dataclass
    must be properly defined with type hints for all fields.
    """
    command = CreateDraftCommand(
        slug="test-post", title="Test Post", author_id=1
    )

    assert hasattr(command, "slug")
    assert hasattr(command, "title")
    assert hasattr(command, "author_id")
    assert isinstance(command.slug, str)
    assert isinstance(command.title, str)
    assert isinstance(command.author_id, int)


def test_command_with_valid_values() -> None:
    """Verify command correctly assigns all field values.

    This test ensures that when creating a CreateDraftCommand with valid
    values, all fields are assigned correctly and can be accessed. The
    command should store the exact values provided during construction.
    """
    slug = "my-first-post"
    title = "My First Post"
    author_id = 42

    command = CreateDraftCommand(slug=slug, title=title, author_id=author_id)

    assert command.slug == slug
    assert command.title == title
    assert command.author_id == author_id


def test_command_with_empty_slug() -> None:
    """Verify command allows empty slug (validation happens in handler).

    This test ensures the command dataclass itself does not perform
    validation. Empty slug should be allowed at the command level, with
    validation deferred to the domain layer (Slug value object) when the
    handler processes the command.
    """
    command = CreateDraftCommand(slug="", title="Valid Title", author_id=1)

    assert command.slug == ""


def test_command_with_empty_title() -> None:
    """Verify command allows empty title (validation happens in handler).

    This test ensures the command dataclass itself does not perform
    validation. Empty title should be allowed at the command level, with
    validation deferred to the domain layer (Post aggregate) when the
    handler processes the command.
    """
    command = CreateDraftCommand(slug="valid-slug", title="", author_id=1)

    assert command.title == ""


def test_command_with_zero_author_id() -> None:
    """Verify command allows zero author_id (validation happens in handler).

    This test ensures the command dataclass itself does not perform
    validation. Zero author_id should be allowed at the command level,
    with validation deferred to the domain layer (Post aggregate) when
    the handler processes the command.
    """
    command = CreateDraftCommand(
        slug="valid-slug", title="Valid Title", author_id=0
    )

    assert command.author_id == 0


def test_command_instances_are_comparable() -> None:
    """Verify command instances can be compared for equality.

    This test ensures dataclass equality works correctly. Two commands
    with identical field values should be equal, while commands with
    different values should not be equal. This supports testing scenarios
    where commands need to be compared.
    """
    command1 = CreateDraftCommand(
        slug="test-post", title="Test Post", author_id=1
    )
    command2 = CreateDraftCommand(
        slug="test-post", title="Test Post", author_id=1
    )
    command3 = CreateDraftCommand(
        slug="different-post", title="Different Post", author_id=2
    )

    assert command1 == command2
    assert command1 != command3
    assert command2 != command3


def test_command_fields_are_immutable() -> None:
    """Verify command fields cannot be modified after creation.

    This test ensures the CreateDraftCommand is immutable by using frozen
    dataclass. Attempting to modify fields after construction should raise
    an error, preventing accidental mutation of command objects.
    """
    command = CreateDraftCommand(
        slug="test-post", title="Test Post", author_id=1
    )

    with pytest.raises((AttributeError, TypeError)):
        command.slug = "modified-slug"

    with pytest.raises((AttributeError, TypeError)):
        command.title = "Modified Title"

    with pytest.raises((AttributeError, TypeError)):
        command.author_id = 999


def test_command_repr_shows_all_fields() -> None:
    """Verify command repr includes all field values for debugging.

    This test ensures the string representation of the command shows all
    field values, which is useful for debugging and logging. The repr
    should clearly identify the command type and show all field values.
    """
    command = CreateDraftCommand(
        slug="test-post", title="Test Post", author_id=1
    )

    repr_str = repr(command)

    assert "CreateDraftCommand" in repr_str
    assert "test-post" in repr_str
    assert "Test Post" in repr_str
    assert "1" in repr_str
