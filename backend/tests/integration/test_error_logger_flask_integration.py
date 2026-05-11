"""Integration tests for ErrorLogger in a Flask error handler context.

These tests verify that ErrorLogger correctly captures entries when used
inside a Flask exception handler — the pattern that will be applied to
handle_unexpected_error() in main.py in Task 6. A minimal Flask app is
used to avoid BUILD_DIR and database dependencies.
"""

import traceback
from collections.abc import Generator
from typing import Never

import pytest
from flask import Flask, jsonify, request
from flask.testing import FlaskClient
from flask.wrappers import Response

from backend.infrastructure.monitoring.error_logger import ErrorLogger


@pytest.fixture(autouse=True)
def _isolate_error_logger() -> Generator[None]:
    """Clear ErrorLogger state before and after every test in this module.

    Autouse ensures no test is contaminated by entries from a prior test, even
    when tests are collected in arbitrary order or re-run selectively.
    """
    ErrorLogger.clear()
    yield
    ErrorLogger.clear()


@pytest.fixture()
def flask_app_with_error_route() -> Flask:
    """Minimal Flask app using ErrorLogger inside an exception handler.

    Registers a catch-all exception handler that calls ErrorLogger.log_error()
    with the same pattern that Task 6 will wire into handle_unexpected_error()
    in main.py. No BUILD_DIR or database is required.
    """
    app = Flask(__name__)
    app.config["TESTING"] = True

    @app.errorhandler(Exception)
    def handle_error(error: Exception) -> tuple[Response, int]:
        """Capture error in ErrorLogger and return 500."""
        endpoint = request.endpoint or "unknown"
        stack_trace = traceback.format_exc()
        ErrorLogger.log_error(
            message=str(error),
            stack_trace=stack_trace,
            endpoint=endpoint,
        )
        return jsonify({"error": "Internal server error"}), 500

    @app.route("/test-trigger-500")
    def trigger_500() -> Never:
        """Raise an unhandled RuntimeError to exercise the 500 handler."""
        raise RuntimeError("intentional test error")

    @app.route("/test-trigger-valueerror")
    def trigger_value_error() -> Never:
        """Raise a ValueError to verify any unhandled exception is logged."""
        raise ValueError("intentional value error")

    return app


@pytest.fixture()
def error_client(flask_app_with_error_route: Flask) -> FlaskClient:
    """Flask test client configured for error-triggering routes."""
    return flask_app_with_error_route.test_client()


class TestErrorLoggerFlaskIntegration:
    """ErrorLogger captures data when used inside a Flask exception handler."""

    def test_500_response_creates_error_logger_entry(
        self, error_client: FlaskClient
    ) -> None:
        """A 500 response causes exactly one entry in ErrorLogger."""
        response = error_client.get("/test-trigger-500")
        assert response.status_code == 500
        errors = ErrorLogger.get_recent_errors()
        assert len(errors) == 1

    def test_error_entry_endpoint_matches_route_name(
        self, error_client: FlaskClient
    ) -> None:
        """The logged entry's endpoint matches the triggering route name."""
        error_client.get("/test-trigger-500")
        errors = ErrorLogger.get_recent_errors()
        assert errors[0].endpoint is not None
        assert (
            "trigger_500" in errors[0].endpoint
            or "/test-trigger-500" in errors[0].endpoint
        )

    def test_error_entry_stack_trace_is_non_empty(
        self, error_client: FlaskClient
    ) -> None:
        """The logged entry contains a non-empty stack trace string."""
        error_client.get("/test-trigger-500")
        errors = ErrorLogger.get_recent_errors()
        assert len(errors[0].stack_trace) > 0

    def test_errors_persist_across_multiple_requests(
        self, error_client: FlaskClient
    ) -> None:
        """Entries accumulate across successive error-triggering requests."""
        error_client.get("/test-trigger-500")
        error_client.get("/test-trigger-valueerror")
        errors = ErrorLogger.get_recent_errors()
        assert len(errors) == 2

    def test_error_isolation_between_tests_via_clear(self) -> None:
        """ErrorLogger is empty at the start of each test due to autouse fixture."""
        assert ErrorLogger.get_recent_errors() == []

    def test_error_message_contains_exception_text(
        self, error_client: FlaskClient
    ) -> None:
        """The logged message includes the exception's string representation."""
        error_client.get("/test-trigger-500")
        errors = ErrorLogger.get_recent_errors()
        assert "intentional test error" in errors[0].message
