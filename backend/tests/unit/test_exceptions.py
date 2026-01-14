import pytest

from backend.exceptions import AuthenticationError, AuthorizationError


class TestAuthenticationError:
    def test_stores_message(self):
        error = AuthenticationError("Token expired")
        assert error.message == "Token expired"

    def test_inherits_from_exception(self):
        error = AuthenticationError("Test error")
        assert isinstance(error, Exception)

    def test_can_be_raised_and_caught(self):
        with pytest.raises(AuthenticationError) as exc_info:
            raise AuthenticationError("Invalid token")
        assert exc_info.value.message == "Invalid token"

    def test_string_representation_includes_message(self):
        error = AuthenticationError("Missing authorization header")
        assert "Missing authorization header" in str(error)

    def test_multiple_instances_are_independent(self):
        error1 = AuthenticationError("Token expired")
        error2 = AuthenticationError("Invalid token")
        assert error1.message == "Token expired"
        assert error2.message == "Invalid token"
        assert error1.message != error2.message

    def test_accepts_empty_message(self):
        error = AuthenticationError("")
        assert error.message == ""

    def test_message_is_accessible_as_args(self):
        error = AuthenticationError("Token validation failed")
        assert "Token validation failed" in error.args


class TestAuthorizationError:
    def test_stores_message_and_required_role(self):
        error = AuthorizationError(
            message="Access denied", required_role="admin"
        )
        assert error.message == "Access denied"
        assert error.required_role == "admin"

    def test_required_role_is_optional(self):
        error = AuthorizationError(message="Insufficient permissions")
        assert error.message == "Insufficient permissions"
        assert error.required_role is None

    def test_inherits_from_exception(self):
        error = AuthorizationError(
            message="Access denied", required_role="admin"
        )
        assert isinstance(error, Exception)

    def test_can_be_raised_and_caught_with_required_role(self):
        with pytest.raises(AuthorizationError) as exc_info:
            raise AuthorizationError(
                message="Access denied", required_role="admin"
            )
        assert exc_info.value.message == "Access denied"
        assert exc_info.value.required_role == "admin"

    def test_can_be_raised_and_caught_without_required_role(self):
        with pytest.raises(AuthorizationError) as exc_info:
            raise AuthorizationError(message="Forbidden")
        assert exc_info.value.message == "Forbidden"
        assert exc_info.value.required_role is None

    def test_string_representation_includes_message(self):
        error = AuthorizationError(
            message="Access denied", required_role="admin"
        )
        assert "Access denied" in str(error)

    def test_multiple_instances_are_independent(self):
        error1 = AuthorizationError(
            message="Access denied", required_role="admin"
        )
        error2 = AuthorizationError(message="Forbidden", required_role="editor")
        assert error1.message == "Access denied"
        assert error1.required_role == "admin"
        assert error2.message == "Forbidden"
        assert error2.required_role == "editor"

    def test_accepts_empty_message(self):
        error = AuthorizationError(message="")
        assert error.message == ""
        assert error.required_role is None

    def test_required_role_can_be_none_explicitly(self):
        error = AuthorizationError(message="Access denied", required_role=None)
        assert error.message == "Access denied"
        assert error.required_role is None

    def test_required_role_can_be_various_role_values(self):
        roles = ["admin", "editor", "viewer", "moderator"]
        for role in roles:
            error = AuthorizationError(
                message="Access denied", required_role=role
            )
            assert error.required_role == role


class TestExceptionHierarchy:
    def test_both_exceptions_inherit_from_base_exception(self):
        auth_error = AuthenticationError("Test")
        authz_error = AuthorizationError(message="Test")
        assert isinstance(auth_error, BaseException)
        assert isinstance(authz_error, BaseException)

    def test_exceptions_are_distinct_types(self):
        auth_error = AuthenticationError("Test")
        authz_error = AuthorizationError(message="Test")
        assert type(auth_error) is not type(authz_error)
        assert not isinstance(auth_error, AuthorizationError)
        assert not isinstance(authz_error, AuthenticationError)

    def test_can_catch_specific_exception_types(self):
        with pytest.raises(AuthenticationError):
            raise AuthenticationError("Token expired")

        with pytest.raises(AuthorizationError):
            raise AuthorizationError(message="Access denied")

    def test_authentication_error_not_caught_by_authorization_error_handler(
        self,
    ):
        with pytest.raises(AuthenticationError):
            try:
                raise AuthenticationError("Token expired")
            except AuthorizationError:
                pytest.fail(
                    "Should not catch AuthenticationError as AuthorizationError"
                )

    def test_authorization_error_not_caught_by_authentication_error_handler(
        self,
    ):
        with pytest.raises(AuthorizationError):
            try:
                raise AuthorizationError(message="Access denied")
            except AuthenticationError:
                pytest.fail(
                    "Should not catch AuthorizationError as AuthenticationError"
                )
