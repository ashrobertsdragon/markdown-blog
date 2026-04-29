"""Unit tests for UnpublishPostCommand dataclass.

Validates the command's primitive constraints per the CQRS pattern:
only structural invariants (positive post_id, positive author_id) are
enforced here. Domain rules (post exists, is published) are deferred
to the handler.

Test Coverage:
- Valid command instantiation with legal values
- Immutability (frozen=True)
- post_id <= 0 raises ValueError
- author_id <= 0 raises ValueError
- Equality comparison
- String representation
"""

import pytest

from backend.application.commands.unpublish_post_command import (
    UnpublishPostCommand,
)


def test_valid_command_does_not_raise() -> None:
    """Verify UnpublishPostCommand accepts positive post_id and author_id.

    This is the baseline happy-path check: a well-formed command must
    construct without raising any exception.
    """
    command = UnpublishPostCommand(
        post_id=42,
        author_id=1,
        user_role="admin",
    )

    assert command.post_id == 42
    assert command.author_id == 1
    assert command.user_role == "admin"


def test_command_with_zero_post_id_raises_value_error() -> None:
    """Verify UnpublishPostCommand rejects post_id of 0.

    post_id must be a positive integer (> 0). A value of 0 is not a
    valid database row reference and must be rejected at construction
    time so the handler never receives an invalid command.
    """
    with pytest.raises(ValueError, match="post_id"):
        UnpublishPostCommand(post_id=0, author_id=1, user_role="admin")


def test_command_with_negative_post_id_raises_value_error() -> None:
    """Verify UnpublishPostCommand rejects negative post_id values.

    Negative IDs cannot correspond to real database rows. The command
    must enforce this constraint in __post_init__ rather than silently
    propagating it to the handler or repository.
    """
    with pytest.raises(ValueError, match="post_id"):
        UnpublishPostCommand(post_id=-5, author_id=1, user_role="admin")


def test_command_with_zero_author_id_raises_value_error() -> None:
    """Verify UnpublishPostCommand rejects author_id of 0."""
    with pytest.raises(ValueError, match="author_id"):
        UnpublishPostCommand(post_id=1, author_id=0, user_role="admin")


def test_command_with_negative_author_id_raises_value_error() -> None:
    """Verify UnpublishPostCommand rejects negative author_id values."""
    with pytest.raises(ValueError, match="author_id"):
        UnpublishPostCommand(post_id=1, author_id=-5, user_role="admin")


def test_command_is_immutable() -> None:
    """Verify UnpublishPostCommand cannot be mutated after construction.

    Commands are value objects in the CQRS sense: they represent a past
    intent and must not be altered in transit. frozen=True on the
    dataclass enforces this at runtime.
    """
    command = UnpublishPostCommand(post_id=1, author_id=1, user_role="admin")

    with pytest.raises((AttributeError, TypeError)):
        command.post_id = 99  # type: ignore[misc]


def test_command_equality_for_identical_fields() -> None:
    """Verify two commands with identical fields compare equal.

    Dataclass equality must hold so commands can be compared in test
    assertions and deduplication logic without resorting to identity
    checks.
    """
    a = UnpublishPostCommand(post_id=42, author_id=7, user_role="admin")
    b = UnpublishPostCommand(post_id=42, author_id=7, user_role="admin")
    c = UnpublishPostCommand(post_id=99, author_id=7, user_role="admin")

    assert a == b
    assert a != c


def test_command_repr_contains_class_name_and_post_id() -> None:
    """Verify repr is informative for debugging and log output.

    The default dataclass repr includes field names and values, which is
    sufficient for tracing command flow through log aggregators.
    """
    command = UnpublishPostCommand(post_id=7, author_id=3, user_role="admin")

    r = repr(command)

    assert "UnpublishPostCommand" in r
    assert "7" in r
