"""Integration tests for ErrorLogger with Flask's handle_unexpected_error hook.

These tests verify that ErrorLogger captures entries when Flask's
handle_unexpected_error() handler fires, that the endpoint field matches the
route name, that stack traces are populated, and that state persists across
requests within a session but is isolated between test runs via clear().

The ErrorLogger integration in handle_unexpected_error() does not exist yet
(Task 6). Tests are expected to fail until that implementation lands.
"""

from collections.abc import Generator
from typing import Never

import pytest
from flask import Flask
from flask.testing import FlaskClient

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
    """Minimal Flask app wired to the production error handler.

    Uses create_app() so that handle_unexpected_error() is registered exactly
    as it will be in production, then adds a test-only route that always raises
    a RuntimeError.
    """
    from backend.main import create_app

    app = create_app()

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
def error_client(
    flask_app_with_error_route: Flask,
    test_settings,
    test_build_dir,
    monkeypatch,
    tmp_path,
) -> FlaskClient:
    """Flask test client configured for error-triggering routes."""
    monkeypatch.setenv("BUILD_DIR", str(test_build_dir))
    monkeypatch.setenv("DRAFTS_PATH", str(tmp_path / "drafts"))
    monkeypatch.setenv("GITHUB_PERSONAL_ACCESS_TOKEN", "test_token")
    monkeypatch.setenv("GITHUB_OWNER", "test_owner")
    monkeypatch.setenv("GITHUB_REPO", "test_repo")
    return flask_app_with_error_route.test_client()


class TestErrorLoggerFlaskIntegration:
    """ErrorLogger captures data from Flask 500 error handler."""

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
