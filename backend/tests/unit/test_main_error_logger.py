"""Unit tests verifying ErrorLogger integration in the real create_app() factory.

These are TDD RED phase tests. They target the NOT-YET-IMPLEMENTED wiring of
ErrorLogger into handle_unexpected_error() and a new 404 handler inside
main.py. All tests must FAIL before implementation and PASS after.
"""

from typing import Never
from unittest.mock import patch

import pytest
from flask import Flask
from flask.testing import FlaskClient

from backend.infrastructure.monitoring.error_logger import ErrorLogger
from backend.main import create_app


@pytest.fixture(autouse=True)
def set_flask_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Force FLASK_ENV=TESTING so create_app() skips production guards."""
    monkeypatch.setenv("FLASK_ENV", "TESTING")


@pytest.fixture()
def app() -> Flask:
    """Real Flask app from create_app() with a runtime-error test route.

    create_schema is patched to prevent database setup from running during
    unit tests. A dedicated /test-trigger-500 route is registered after
    app creation so the real error handler is exercised without polluting
    the production route map.
    """
    with patch("backend.main.create_schema"):
        flask_app = create_app()

    @flask_app.route("/test-trigger-500")
    def trigger_500() -> Never:
        """Raise RuntimeError to trigger the 500 error handler."""
        raise RuntimeError("unit test runtime error")

    return flask_app


@pytest.fixture()
def client(app: Flask) -> FlaskClient:
    """Test client bound to the real create_app() Flask instance."""
    return app.test_client()


class TestHandle500LogsToErrorLogger:
    """handle_unexpected_error() must call ErrorLogger.log_error() for non-HTTP exceptions."""

    def test_500_creates_exactly_one_error_entry(
        self, client: FlaskClient
    ) -> None:
        """An unhandled RuntimeError produces exactly one ErrorLogger entry."""
        response = client.get("/test-trigger-500")

        assert response.status_code == 500
        errors = ErrorLogger.get_recent_errors()
        assert len(errors) == 1

    def test_500_error_message_contains_exception_text(
        self, client: FlaskClient
    ) -> None:
        """The logged entry's message reflects the original exception text."""
        client.get("/test-trigger-500")

        errors = ErrorLogger.get_recent_errors()
        assert "unit test runtime error" in errors[0].message

    def test_500_error_stack_trace_is_non_empty(
        self, client: FlaskClient
    ) -> None:
        """The logged entry contains a non-empty stack trace."""
        client.get("/test-trigger-500")

        errors = ErrorLogger.get_recent_errors()
        assert len(errors[0].stack_trace) > 0

    def test_500_error_stack_trace_contains_traceback_keyword(
        self, client: FlaskClient
    ) -> None:
        """The stack trace string includes recognisable traceback text."""
        client.get("/test-trigger-500")

        errors = ErrorLogger.get_recent_errors()
        assert "Traceback" in errors[0].stack_trace

    def test_500_error_captures_endpoint_or_path(
        self, client: FlaskClient
    ) -> None:
        """The logged entry's endpoint field is non-None and identifies the route."""
        client.get("/test-trigger-500")

        errors = ErrorLogger.get_recent_errors()
        assert errors[0].endpoint is not None
        assert len(errors[0].endpoint) > 0

    def test_500_endpoint_contains_route_identifier(
        self, client: FlaskClient
    ) -> None:
        """The endpoint field references the triggering route name or path."""
        client.get("/test-trigger-500")

        errors = ErrorLogger.get_recent_errors()
        endpoint = errors[0].endpoint or ""
        assert "trigger_500" in endpoint or "/test-trigger-500" in endpoint


class TestHandle404LogsToErrorLogger:
    """A new @app.errorhandler(404) must log 404 errors to ErrorLogger."""

    def test_404_creates_exactly_one_error_entry(
        self, client: FlaskClient
    ) -> None:
        """A request to a non-existent route produces exactly one ErrorLogger entry."""
        response = client.get("/api/this-route-does-not-exist")

        assert response.status_code == 404
        errors = ErrorLogger.get_recent_errors()
        assert len(errors) == 1

    def test_404_error_message_is_non_empty(self, client: FlaskClient) -> None:
        """The logged 404 entry has a non-empty message."""
        client.get("/api/this-route-does-not-exist")

        errors = ErrorLogger.get_recent_errors()
        assert len(errors[0].message) > 0

    def test_404_error_captures_endpoint_or_path(
        self, client: FlaskClient
    ) -> None:
        """The logged 404 entry has a non-None endpoint field."""
        client.get("/api/this-route-does-not-exist")

        errors = ErrorLogger.get_recent_errors()
        assert errors[0].endpoint is not None


class TestErrorLoggerIsolation:
    """Autouse clear_error_logger_after_test fixture keeps tests independent."""

    def test_error_logger_is_empty_at_test_start(self) -> None:
        """ErrorLogger contains no entries at the start of each test."""
        assert ErrorLogger.get_recent_errors() == []

    def test_http_exceptions_do_not_log_to_error_logger(
        self, client: FlaskClient
    ) -> None:
        """HTTPExceptions (werkzeug) below 500 are not forwarded to ErrorLogger.

        The existing handle_unexpected_error() already guards with
        isinstance(error, HTTPException). This test confirms that guard is
        preserved — no double-logging of werkzeug HTTP errors other than 404.
        The 401 route is provided by the auth blueprint; any 401 scenario
        that comes from AuthenticationError (a non-HTTP domain exception) is
        handled by a separate handler. We use a werkzeug-level 405 here.
        """
        client.post("/api/health")

        errors = ErrorLogger.get_recent_errors()
        assert len(errors) == 0
