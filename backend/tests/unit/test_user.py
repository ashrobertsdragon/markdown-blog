"""Unit tests for User aggregate.

This module defines comprehensive tests for the User aggregate following TDD
Red phase principles. These tests will initially fail until the User aggregate
is implemented.

Test Coverage:
- Factory method tests (4 tests)
- Role change tests (4 tests)
- Serialization tests (3 tests)
- Edge cases and validation (4 tests)
"""

import datetime as dt
from datetime import datetime

import pytest
from backend.domain.aggregates.user import User

from backend.domain.value_objects.role import Role


def test_create_from_clerk_sets_correct_fields() -> None:
    """Verify factory method sets all fields correctly.

    This test ensures that when creating a User from Clerk data,
    all required fields are populated with the expected values.
    The factory method should accept clerk_user_id and email,
    and initialize the User with these values plus defaults.
    """
    clerk_user_id = "user_2NJxGbPQaBCdef123"
    email = "test@example.com"

    user = User.create_from_clerk(clerk_user_id, email)

    assert user.clerk_user_id == clerk_user_id
    assert user.email == email
    assert isinstance(user.role, Role)
    assert isinstance(user.created_at, datetime)


def test_create_from_clerk_defaults_to_authenticated_role() -> None:
    """Verify new users default to AUTHENTICATED role.

    This test ensures business rule compliance: newly registered users
    must start with the AUTHENTICATED role for security purposes.
    Elevation to AUTHOR or ADMIN roles requires explicit admin action.
    """
    user = User.create_from_clerk("user_abc123", "user@example.com")

    assert user.role == Role.AUTHENTICATED


def test_create_from_clerk_has_no_id_until_persisted() -> None:
    """Verify new users have no database ID until persisted.

    This test validates the aggregate state lifecycle: entities created
    in memory should not have a database ID until they are persisted
    by a repository. The id field should be None for unpersisted entities.
    """
    user = User.create_from_clerk("user_xyz789", "new@example.com")

    assert user.id is None


def test_create_from_clerk_sets_created_at_timestamp() -> None:
    """Verify created_at timestamp is set to current time.

    This test ensures audit trail requirements: the created_at field
    must be automatically populated with the current UTC timestamp
    when a user is created. Timestamp must be recent (within 1 second).
    """
    before = datetime.now(dt.UTC)
    user = User.create_from_clerk("user_123abc", "timestamp@example.com")
    after = datetime.now(dt.UTC)

    assert before <= user.created_at <= after
    assert (user.created_at - before).total_seconds() < 1


def test_change_role_updates_role_field() -> None:
    """Verify change_role method updates the role field.

    This test validates the core role change behavior: calling
    change_role with a new Role should update the user's role field
    to the new value. This is the primary mutation allowed on User.
    """
    user = User.create_from_clerk("user_role123", "role@example.com")
    original_role = user.role

    user.change_role(Role.AUTHOR)

    assert user.role == Role.AUTHOR
    assert user.role != original_role


def test_change_role_from_authenticated_to_author() -> None:
    """Verify role transition from AUTHENTICATED to AUTHOR.

    This test validates a specific business workflow: promoting a
    basic authenticated user to author status. This is the typical
    path for users who want to create blog content.
    """
    user = User.create_from_clerk("user_promote1", "author@example.com")
    assert user.role == Role.AUTHENTICATED

    user.change_role(Role.AUTHOR)

    assert user.role == Role.AUTHOR
    assert user.role.can_access_author_endpoints() is True


def test_change_role_from_author_to_admin() -> None:
    """Verify role transition from AUTHOR to ADMIN.

    This test validates admin promotion workflow: elevating an author
    to administrator status. This grants full system access and is
    typically reserved for trusted content creators.
    """
    user = User.create_from_clerk("user_promote2", "admin@example.com")
    user.change_role(Role.AUTHOR)
    assert user.role == Role.AUTHOR

    user.change_role(Role.ADMIN)

    assert user.role == Role.ADMIN
    assert user.role.can_access_admin_endpoints() is True


def test_change_role_to_same_role_is_allowed() -> None:
    """Verify changing to the same role is idempotent.

    This test ensures defensive programming: setting a role to its
    current value should succeed without errors. This supports
    idempotent operations and simplifies calling code that may not
    check current role before updating.
    """
    user = User.create_from_clerk("user_idempotent", "same@example.com")
    user.change_role(Role.AUTHOR)

    user.change_role(Role.AUTHOR)

    assert user.role == Role.AUTHOR


def test_to_dict_includes_all_fields() -> None:
    """Verify serialization includes all User fields.

    This test ensures API contract compliance: the to_dict method
    must serialize all User fields for API responses. Missing fields
    would break client expectations and API contracts.
    """
    user = User.create_from_clerk("user_serialize", "serialize@example.com")
    user.change_role(Role.AUTHOR)

    user_dict = user.to_dict()

    assert "id" in user_dict
    assert "clerk_user_id" in user_dict
    assert "email" in user_dict
    assert "role" in user_dict
    assert "created_at" in user_dict


def test_to_dict_serializes_role_as_string() -> None:
    """Verify role is serialized as string, not enum object.

    This test ensures JSON compatibility: the role field must be
    serialized as a string value (e.g., 'author') rather than an
    enum object, since enum objects are not JSON-serializable.
    """
    user = User.create_from_clerk("user_role_str", "rolestr@example.com")
    user.change_role(Role.ADMIN)

    user_dict = user.to_dict()

    assert isinstance(user_dict["role"], str)
    assert user_dict["role"] == "admin"


def test_to_dict_handles_none_id_correctly() -> None:
    """Verify None id is serialized correctly for unpersisted users.

    This test ensures proper handling of unpersisted entities: users
    that haven't been saved to the database should serialize their
    id field as None, which is valid JSON and signals unpersisted state.
    """
    user = User.create_from_clerk("user_none_id", "noneid@example.com")
    assert user.id is None

    user_dict = user.to_dict()

    assert user_dict["id"] is None


def test_create_from_clerk_with_empty_email_fails() -> None:
    """Verify empty email validation fails fast.

    This test enforces input validation at the domain boundary:
    creating a User with an empty email should raise a ValueError
    because email is a required business identifier. Failing fast
    prevents invalid aggregates from being created.
    """
    with pytest.raises(ValueError, match="email"):
        User.create_from_clerk("user_noemail", "")


def test_create_from_clerk_with_empty_clerk_id_fails() -> None:
    """Verify empty Clerk ID validation fails fast.

    This test enforces external identity validation: the clerk_user_id
    is the primary link to the authentication system and cannot be
    empty. Empty values would break authentication integration.
    """
    with pytest.raises(ValueError, match="clerk_user_id"):
        User.create_from_clerk("", "valid@example.com")


def test_user_created_at_is_immutable() -> None:
    """Verify created_at timestamp cannot be modified after creation.

    This test enforces audit trail integrity: the created_at field
    represents when the user was first created and must never change.
    Attempting to modify it should raise an error, ensuring historical
    accuracy of user creation timestamps.
    """
    user = User.create_from_clerk("user_immutable", "immutable@example.com")
    original_created_at = user.created_at

    with pytest.raises(AttributeError):
        user.created_at = datetime.now(dt.UTC)

    assert user.created_at == original_created_at
