"""Unit tests for UnpublishPostCommand dataclass.

Validates the command's primitive constraints per the CQRS pattern:
only structural invariants (non-empty slug, positive author_id) are
enforced here. Domain rules (post exists, is published) are deferred
to the handler.

Test Coverage:
- Valid command instantiation with legal values
- Immutability (frozen=True)
- author_id <= 0 raises ValueError
- Empty slug raises ValueError
- Equality comparison
- String representation
"""

import pytest

from backend.application.commands.unpublish_post_command import (
    UnpublishPostCommand,
)


def test_valid_command_does_not_raise() -> None:
    """Verify UnpublishPostCommand accepts a positive author_id and non-empty slug.

    This is the baseline happy-path check: a well-formed command must
    construct without raising any exception.
    """
    command = UnpublishPostCommand(
        slug="my-published-post",
        author_id=1,
        user_role="admin",
    )

    assert command.slug == "my-published-post"
    assert command.author_id == 1
    assert command.user_role == "admin"


def test_command_with_zero_author_id_raises_value_error() -> None:
    """Verify UnpublishPostCommand rejects author_id of 0.

    author_id must be a positive integer (> 0). A value of 0 is not a
    valid user reference and must be rejected at construction time so
    the handler never receives an invalid command.
    """
    with pytest.raises(ValueError, match="author_id"):
        UnpublishPostCommand(slug="valid-slug", author_id=0, user_role="admin")


def test_command_with_negative_author_id_raises_value_error() -> None:
    """Verify UnpublishPostCommand rejects negative author_id values.

    Negative IDs cannot correspond to real database rows. The command
    must enforce this constraint in __post_init__ rather than silently
    propagating it to the handler or repository.
    """
    with pytest.raises(ValueError, match="author_id"):
        UnpublishPostCommand(slug="valid-slug", author_id=-5, user_role="admin")


def test_command_with_empty_slug_raises_value_error() -> None:
    """Verify UnpublishPostCommand rejects an empty slug string.

    An empty string cannot identify a post. The command validates this
    primitive constraint so that find_by_slug is never called with a
    meaningless lookup key.
    """
    with pytest.raises(ValueError):
        UnpublishPostCommand(slug="", author_id=1, user_role="admin")


def test_command_is_immutable() -> None:
    """Verify UnpublishPostCommand cannot be mutated after construction.

    Commands are value objects in the CQRS sense: they represent a past
    intent and must not be altered in transit. frozen=True on the
    dataclass enforces this at runtime.
    """
    command = UnpublishPostCommand(
        slug="immutable-post", author_id=1, user_role="admin"
    )

    with pytest.raises((AttributeError, TypeError)):
        command.slug = "changed"  # type: ignore[misc]


def test_command_equality_for_identical_fields() -> None:
    """Verify two commands with identical fields compare equal.

    Dataclass equality must hold so commands can be compared in test
    assertions and deduplication logic without resorting to identity
    checks.
    """
    a = UnpublishPostCommand(slug="same-post", author_id=42, user_role="admin")
    b = UnpublishPostCommand(slug="same-post", author_id=42, user_role="admin")
    c = UnpublishPostCommand(slug="other-post", author_id=42, user_role="admin")

    assert a == b
    assert a != c


def test_command_repr_contains_class_name_and_slug() -> None:
    """Verify repr is informative for debugging and log output.

    The default dataclass repr includes field names and values, which is
    sufficient for tracing command flow through log aggregators.
    """
    command = UnpublishPostCommand(
        slug="debug-post", author_id=7, user_role="admin"
    )

    r = repr(command)

    assert "UnpublishPostCommand" in r
    assert "debug-post" in r
