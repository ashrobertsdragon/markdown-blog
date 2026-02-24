from enum import StrEnum

import pytest

from backend.domain.value_objects.role import Role


def test_authenticated_role_has_correct_string_value() -> None:
    assert Role.AUTHENTICATED.value == "authenticated"


def test_author_role_has_correct_string_value() -> None:
    assert Role.AUTHOR.value == "author"


def test_admin_role_has_correct_string_value() -> None:
    assert Role.ADMIN.value == "admin"


def test_role_can_be_created_from_string_authenticated() -> None:
    role = Role("authenticated")
    assert role == Role.AUTHENTICATED


def test_role_can_be_created_from_string_author() -> None:
    role = Role("author")
    assert role == Role.AUTHOR


def test_role_can_be_created_from_string_admin() -> None:
    role = Role("admin")
    assert role == Role.ADMIN


def test_role_string_conversion_returns_lowercase_value() -> None:
    assert str(Role.AUTHENTICATED) == "authenticated"
    assert str(Role.AUTHOR) == "author"
    assert str(Role.ADMIN) == "admin"


def test_role_invalid_string_raises_value_error() -> None:
    with pytest.raises(ValueError, match="'invalid_role' is not a valid Role"):
        Role("invalid_role")


def test_role_empty_string_raises_value_error() -> None:
    with pytest.raises(ValueError):
        Role("")


def test_role_uppercase_string_raises_value_error() -> None:
    with pytest.raises(ValueError):
        Role("ADMIN")


def test_authenticated_cannot_access_author_endpoints() -> None:
    assert Role.AUTHENTICATED.can_access_author_endpoints() is False


def test_author_can_access_author_endpoints() -> None:
    assert Role.AUTHOR.can_access_author_endpoints() is True


def test_admin_can_access_author_endpoints() -> None:
    assert Role.ADMIN.can_access_author_endpoints() is True


def test_authenticated_cannot_access_admin_endpoints() -> None:
    assert Role.AUTHENTICATED.can_access_admin_endpoints() is False


def test_author_cannot_access_admin_endpoints() -> None:
    assert Role.AUTHOR.can_access_admin_endpoints() is False


def test_admin_can_access_admin_endpoints() -> None:
    assert Role.ADMIN.can_access_admin_endpoints() is True


def test_role_instances_are_hashable() -> None:
    role_dict = {
        Role.AUTHENTICATED: "basic_user",
        Role.AUTHOR: "content_creator",
        Role.ADMIN: "administrator",
    }
    assert role_dict[Role.AUTHENTICATED] == "basic_user"
    assert role_dict[Role.AUTHOR] == "content_creator"
    assert role_dict[Role.ADMIN] == "administrator"


def test_role_instances_can_be_used_in_sets() -> None:
    role_set = {Role.AUTHENTICATED, Role.AUTHOR, Role.ADMIN}
    assert len(role_set) == 3
    assert Role.AUTHENTICATED in role_set
    assert Role.AUTHOR in role_set
    assert Role.ADMIN in role_set


def test_role_members_are_immutable() -> None:
    with pytest.raises(AttributeError):
        setattr(Role.ADMIN, "value", "modified")


def test_role_string_comparison_authenticated() -> None:
    assert Role.AUTHENTICATED == "authenticated"


def test_role_string_comparison_author() -> None:
    assert Role.AUTHOR == "author"


def test_role_string_comparison_admin() -> None:
    assert Role.ADMIN == "admin"


def test_role_is_subclass_of_str_enum() -> None:
    assert issubclass(Role, StrEnum)


def test_role_instance_is_str_enum() -> None:
    assert isinstance(Role.ADMIN, StrEnum)


def test_role_iteration_yields_all_three_members() -> None:
    roles = list(Role)
    assert len(roles) == 3
    assert Role.AUTHENTICATED in roles
    assert Role.AUTHOR in roles
    assert Role.ADMIN in roles


def test_role_member_count_is_three() -> None:
    assert len(Role) == 3


def test_role_name_property_authenticated() -> None:
    assert Role.AUTHENTICATED.name == "AUTHENTICATED"


def test_role_name_property_author() -> None:
    assert Role.AUTHOR.name == "AUTHOR"


def test_role_name_property_admin() -> None:
    assert Role.ADMIN.name == "ADMIN"


def test_role_equality_between_same_roles() -> None:
    role1 = Role.ADMIN
    role2 = Role.ADMIN
    assert role1 == role2
    assert role1 is role2


def test_role_inequality_between_different_roles() -> None:
    assert Role.AUTHENTICATED != Role.AUTHOR
    assert Role.AUTHOR != Role.ADMIN
    assert Role.AUTHENTICATED != Role.ADMIN


def test_role_comparison_with_invalid_type_returns_false() -> None:
    assert Role.ADMIN != 123
    assert Role.ADMIN is not None
    assert Role.ADMIN != []


@pytest.mark.parametrize(
    "role,expected_author_access",
    [
        (Role.AUTHENTICATED, False),
        (Role.AUTHOR, True),
        (Role.ADMIN, True),
    ],
)
def test_can_access_author_endpoints_parametrized(
    role: Role, expected_author_access: bool
) -> None:
    assert role.can_access_author_endpoints() == expected_author_access


@pytest.mark.parametrize(
    "role,expected_admin_access",
    [
        (Role.AUTHENTICATED, False),
        (Role.AUTHOR, False),
        (Role.ADMIN, True),
    ],
)
def test_can_access_admin_endpoints_parametrized(
    role: Role, expected_admin_access: bool
) -> None:
    assert role.can_access_admin_endpoints() == expected_admin_access


def test_role_can_be_serialized_to_string() -> None:
    import json

    role_data = {"user_role": str(Role.ADMIN)}
    serialized = json.dumps(role_data)
    assert "admin" in serialized


def test_role_can_be_deserialized_from_string() -> None:
    import json

    serialized = '{"user_role": "author"}'
    data = json.loads(serialized)
    role = Role(data["user_role"])
    assert role == Role.AUTHOR
