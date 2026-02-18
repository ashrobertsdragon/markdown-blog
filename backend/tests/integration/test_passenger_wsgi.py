"""Integration tests for Passenger WSGI entry point.

Tests WSGI interface compliance for patched_passenger_wsgi.py module.
This module must expose an 'application' variable that is a WSGI-compliant
Flask application instance.
"""

import os
from unittest.mock import patch

import pytest
from flask import Flask
from flask.testing import FlaskClient


@pytest.fixture
def patched_passenger_wsgi(monkeypatch):
    """Fixture to import and return patched_passenger_wsgi module."""
    monkeypatch.setenv("FLASK_ENV", "TESTING")
    import passenger_wsgi

    return passenger_wsgi


@pytest.fixture
def mock_virtualenv() -> str:
    """Fixture providing a mock virtual environment path."""
    return os.path.join("home", "cpaneluser", "virtualenv", "blog")


@pytest.fixture
def mock_interpreter_path() -> str:
    """Fixture providing a mock interpreter path."""
    return os.path.join(
        "home", "cpaneluser", "virtualenv", "blog", "bin", "python3"
    )


@pytest.fixture
def flask_test_client(patched_passenger_wsgi) -> FlaskClient:
    app: Flask = patched_passenger_wsgi.application
    return app.test_client()


def test_application_variable_exists(patched_passenger_wsgi):
    """patched_passenger_wsgi module must expose 'application' variable.

    Passenger looks for module-level variable named 'application', not 'app'.
    """
    with patch("os.execl"):
        assert hasattr(patched_passenger_wsgi, "application"), (
            "patched_passenger_wsgi module must expose 'application' variable"
        )


def test_application_is_flask_app(patched_passenger_wsgi):
    """application variable must be a Flask instance."""
    from flask import Flask

    with patch("os.execl"):
        assert isinstance(patched_passenger_wsgi.application, Flask), (
            "application must be a Flask instance"
        )


def test_application_is_callable(patched_passenger_wsgi):
    """application must be callable to satisfy WSGI spec.

    WSGI spec requires application to be a callable that accepts
    environ and start_response parameters.
    """
    with patch("os.execl"):
        assert callable(patched_passenger_wsgi.application), (
            "application must be callable per WSGI spec"
        )


def test_application_handles_basic_request(flask_test_client):
    """application should handle basic HTTP requests through WSGI interface.

    Tests that the WSGI application can process a basic request using
    Flask's test client, which simulates WSGI environ/start_response.
    """
    with patch("os.execl"):
        response = flask_test_client.get("/api/health")

        assert response.status_code in (
            200,
            503,
        ), "application should respond to health check"
        assert response.content_type == "application/json", (
            "application should return JSON responses"
        )


def test_health_endpoint_via_wsgi(flask_test_client):
    """Health endpoint should be accessible through WSGI application.

    Verifies that blueprints are properly registered and routes work
    through the WSGI interface.
    """
    with patch("os.execl"):
        response = flask_test_client.get("/api/health")

        assert response.status_code == 200, "health endpoint should return 200"
        assert response.json is not None, "health endpoint should return JSON"
        assert "status" in response.json, (
            "health endpoint should include status field"
        )


def test_ensure_virtualenv_loads_correct_python_env(
    patched_passenger_wsgi, mock_virtualenv, mock_interpreter_path
):
    """ensure_virtualenv should pass the correct interpreter to os.execl()."""
    with (
        patch("os.path.exists", return_value=True),
        patch("os.execl") as mock_execl,
        patch("sys.executable", "/usr/bin/python3"),
        patch("sys.platform", "linux"),
    ):
        patched_passenger_wsgi.ensure_virtualenv(mock_virtualenv)
        assert mock_execl.call_args[0][0] == mock_interpreter_path


def test_ensure_virtualenv_raises_value_error_with_no_path(
    patched_passenger_wsgi, monkeypatch
):
    """ensure_virtualenv should raise a ValueError when no path is set."""
    monkeypatch.delenv("VENV_PATH", raising=False)
    with pytest.raises(ValueError) as exec_info:
        patched_passenger_wsgi.ensure_virtualenv()
    assert str(exec_info.value) == "Virtual Environment path must be set"


def test_ensure_virtualenv_uses_envvar(patched_passenger_wsgi, monkeypatch):
    """ensure_virtualenv should use environment value as fallback."""
    monkeypatch.setenv("VENV_PATH", "test_path")
    with (
        patch("os.path.exists", return_value=True),
        patch("os.execl") as mock_execl,
        patch("sys.executable", "/usr/bin/python3"),
        patch("sys.platform", "linux"),
    ):
        patched_passenger_wsgi.ensure_virtualenv()
        assert mock_execl.call_args[0][0] == os.path.join(
            "test_path", "bin", "python3"
        )


def test_ensure_virtualenv_uses_arg_over_envvar(
    patched_passenger_wsgi, mock_virtualenv, mock_interpreter_path, monkeypatch
):
    """ensure_virtualenv should use argument value over environment value."""
    monkeypatch.setenv("VENV_PATH", "test_path")
    with (
        patch("os.path.exists", return_value=True),
        patch("os.execl") as mock_execl,
        patch("sys.executable", "/usr/bin/python3"),
        patch("sys.platform", "linux"),
    ):
        patched_passenger_wsgi.ensure_virtualenv(mock_virtualenv)
        assert mock_execl.call_args[0][0] == mock_interpreter_path
