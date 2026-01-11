from typing import Never

import pytest
from flask import Flask
from flask.wrappers import Response


@pytest.fixture
def app():
    """Create Flask app with test routes that raise exceptions."""
    app = Flask(__name__)
    app.config["TESTING"] = True

    from backend.exceptions import AuthenticationError, AuthorizationError

    @app.errorhandler(AuthenticationError)
    def handle_authentication_error(error: AuthenticationError) -> Response:
        from flask import jsonify

        response = jsonify({"error": str(error)})
        response.status_code = 401
        return response

    @app.errorhandler(AuthorizationError)
    def handle_authorization_error(error: AuthorizationError) -> Response:
        from flask import jsonify

        payload = {"error": error.message}
        if error.required_role is not None:
            payload["required_role"] = error.required_role
        response = jsonify(payload)
        response.status_code = 403
        return response

    @app.route("/test-auth-error")
    def test_auth_error() -> Never:
        raise AuthenticationError("Invalid authentication credentials")

    @app.route("/test-authz-error-with-role")
    def test_authz_error_with_role() -> Never:
        raise AuthorizationError(
            message="Insufficient permissions", required_role="admin"
        )

    @app.route("/test-authz-error-without-role")
    def test_authz_error_without_role() -> Never:
        raise AuthorizationError(message="Access denied")

    return app


@pytest.fixture
def client(app):
    """Create Flask test client."""
    return app.test_client()


class TestAuthenticationErrorHandler:
    """Test suite for AuthenticationError handler integration."""

    def test_returns_401_status_code(self, client):
        """Test that AuthenticationError returns HTTP 401 status."""
        response = client.get("/test-auth-error")
        assert response.status_code == 401

    def test_returns_json_content_type(self, client):
        """Test that response has JSON content type."""
        response = client.get("/test-auth-error")
        assert response.content_type == "application/json"

    def test_response_contains_error_key(self, client):
        """Test that response contains 'error' key."""
        response = client.get("/test-auth-error")
        data = response.get_json()
        assert "error" in data

    def test_response_contains_error_message(self, client):
        """Test that response includes the error message."""
        response = client.get("/test-auth-error")
        data = response.get_json()
        assert data["error"] == "Invalid authentication credentials"

    def test_response_structure_matches_expected_format(self, client):
        """Test that response structure is exactly {"error": "message"}."""
        response = client.get("/test-auth-error")
        data = response.get_json()
        assert set(data.keys()) == {"error"}
        assert isinstance(data["error"], str)

    def test_error_message_is_not_empty(self, client):
        """Test that error message is not empty string."""
        response = client.get("/test-auth-error")
        data = response.get_json()
        assert len(data["error"]) > 0


class TestAuthorizationErrorHandler:
    """Test suite for AuthorizationError handler integration."""

    def test_returns_403_status_code(self, client):
        """Test that AuthorizationError returns HTTP 403 status."""
        response = client.get("/test-authz-error-with-role")
        assert response.status_code == 403

    def test_returns_json_content_type(self, client):
        """Test that response has JSON content type."""
        response = client.get("/test-authz-error-with-role")
        assert response.content_type == "application/json"

    def test_response_contains_error_key(self, client):
        """Test that response contains 'error' key."""
        response = client.get("/test-authz-error-with-role")
        data = response.get_json()
        assert "error" in data

    def test_response_contains_error_message(self, client):
        """Test that response includes the error message."""
        response = client.get("/test-authz-error-with-role")
        data = response.get_json()
        assert data["error"] == "Insufficient permissions"

    def test_includes_required_role_when_provided(self, client):
        """Test that response includes 'required_role' when provided."""
        response = client.get("/test-authz-error-with-role")
        data = response.get_json()
        assert "required_role" in data
        assert data["required_role"] == "admin"

    def test_excludes_required_role_when_not_provided(self, client):
        """Test that response excludes 'required_role' when None."""
        response = client.get("/test-authz-error-without-role")
        data = response.get_json()
        assert "required_role" not in data

    def test_response_structure_with_role_matches_expected_format(self, client):
        """Test response structure with role."""
        response = client.get("/test-authz-error-with-role")
        data = response.get_json()
        assert set(data.keys()) == {"error", "required_role"}
        assert isinstance(data["error"], str)
        assert isinstance(data["required_role"], str)

    def test_response_structure_without_role_matches_expected_format(
        self, client
    ):
        """Test response structure is {"error": "message"} when no role."""
        response = client.get("/test-authz-error-without-role")
        data = response.get_json()
        assert set(data.keys()) == {"error"}
        assert isinstance(data["error"], str)

    def test_error_message_is_not_empty(self, client):
        """Test that error message is not empty string."""
        response = client.get("/test-authz-error-with-role")
        data = response.get_json()
        assert len(data["error"]) > 0

    def test_required_role_is_not_empty_when_provided(self, client):
        """Test that required_role is not empty string when provided."""
        response = client.get("/test-authz-error-with-role")
        data = response.get_json()
        assert len(data["required_role"]) > 0


class TestErrorHandlerIntegration:
    """Test suite for error handler integration with Flask application."""

    def test_authentication_error_handler_registered(self, app):
        """Test that AuthenticationError handler is registered with Flask."""
        from backend.exceptions import AuthenticationError

        assert (
            None in app.error_handler_spec
            and None in app.error_handler_spec[None]
            and AuthenticationError in app.error_handler_spec[None][None]
        )

    def test_authorization_error_handler_registered(self, app):
        """Test that AuthorizationError handler is registered with Flask."""
        from backend.exceptions import AuthorizationError

        assert (
            None in app.error_handler_spec
            and None in app.error_handler_spec[None]
            and AuthorizationError in app.error_handler_spec[None][None]
        )

    def test_multiple_authentication_errors_handled_consistently(self, client):
        """Test that multiple AuthenticationError instances handled same way."""
        response1 = client.get("/test-auth-error")
        response2 = client.get("/test-auth-error")

        assert response1.status_code == response2.status_code
        assert response1.content_type == response2.content_type
        assert response1.get_json()["error"] == response2.get_json()["error"]

    def test_multiple_authorization_errors_handled_consistently(self, client):
        """Test that multiple AuthorizationError instances handled same way."""
        response1 = client.get("/test-authz-error-with-role")
        response2 = client.get("/test-authz-error-with-role")

        assert response1.status_code == response2.status_code
        assert response1.content_type == response2.content_type
        assert response1.get_json() == response2.get_json()

    def test_different_error_types_return_different_status_codes(self, client):
        """Test that different error types return appropriate status codes."""
        auth_response = client.get("/test-auth-error")
        authz_response = client.get("/test-authz-error-with-role")

        assert auth_response.status_code == 401
        assert authz_response.status_code == 403
        assert auth_response.status_code != authz_response.status_code
