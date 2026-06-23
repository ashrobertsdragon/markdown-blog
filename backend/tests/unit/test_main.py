"""Unit tests for Flask application factory.

Tests the create_app() factory function that initializes and configures
the Flask application with proper settings, blueprints, and CORS handling.

These are TDD RED phase tests - they will FAIL until create_app() is
implemented.
"""

from pathlib import Path
from unittest.mock import patch

import pytest
from flask import Flask

from backend.main import create_app


@pytest.fixture(autouse=True)
def set_flask_env(monkeypatch):
    monkeypatch.setenv("FLASK_ENV", "TESTING")


def test_create_app_returns_flask_instance():
    """create_app() should return a Flask application instance."""

    app = create_app()

    assert isinstance(app, Flask)


def test_create_app_configures_static_folder():
    """create_app() configures static_folder to build/static."""

    expected_static_path = Path(__file__).parents[3] / "build" / "static"

    app = create_app()

    assert app.static_folder == str(expected_static_path)


def test_create_app_respects_static_path_override(monkeypatch):
    """create_app() should respect STATIC_PATH environment variable."""

    monkeypatch.setenv("STATIC_PATH", "custom_static")

    app = create_app()

    assert app.static_folder and app.static_folder.endswith("custom_static")


def test_create_app_configures_template_folder():
    """create_app() should configure template_folder to build dir."""

    expected_template_path = Path(__file__).parents[3] / "build"

    app = create_app()

    assert app.template_folder is not None
    assert Path(app.template_folder) == expected_template_path


def test_create_app_registers_health_blueprint():
    """create_app() should register the health check blueprint."""

    app = create_app()

    assert "health" in app.blueprints


def test_create_app_enables_cors_in_development(monkeypatch):
    """create_app() should enable CORS when FLASK_ENV=DEVELOPMENT."""

    monkeypatch.setenv("FLASK_ENV", "DEVELOPMENT")

    with patch("backend.main.CORS") as mock_cors:
        app = create_app()
        mock_cors.assert_called_once_with(app)


def test_create_app_disables_cors_in_production(monkeypatch):
    """create_app() should NOT enable CORS when FLASK_ENV=PRODUCTION."""

    monkeypatch.setenv("FLASK_ENV", "PRODUCTION")

    with (
        patch("pathlib.Path.exists", return_value=True),
        patch("backend.main.CORS") as mock_cors,
        patch("backend.main.run_migrations"),
        patch("backend.main.get_engine"),
    ):
        create_app()
        mock_cors.assert_not_called()


def test_create_app_raises_error_on_missing_build_in_production(monkeypatch):
    """Raise RuntimeError when build dir missing in production."""

    monkeypatch.setenv("FLASK_ENV", "PRODUCTION")

    with (
        patch("pathlib.Path.exists", return_value=False),
        pytest.raises(RuntimeError, match="Frontend build directory not found"),
    ):
        create_app()


def test_create_app_logs_warning_on_missing_build_in_development(
    monkeypatch, caplog
):
    """create_app() should log warning when build missing in development."""

    monkeypatch.setenv("FLASK_ENV", "DEVELOPMENT")

    with patch("pathlib.Path.exists", return_value=False):
        app = create_app()

    assert "Frontend build directory not found" in caplog.text
    assert isinstance(app, Flask)


def test_create_app_respects_flask_env_from_environment(monkeypatch):
    """create_app() should respect FLASK_ENV environment variable."""

    monkeypatch.setenv("FLASK_ENV", "DEVELOPMENT")

    with patch("backend.main.CORS") as mock_cors:
        create_app()

    mock_cors.assert_called_once()


def test_create_app_handles_missing_flask_env_gracefully(monkeypatch):
    """create_app() should default to production when FLASK_ENV not set."""

    monkeypatch.delenv("FLASK_ENV", raising=False)

    with (
        patch("pathlib.Path.exists", return_value=True),
        patch("backend.main.CORS") as mock_cors,
        patch("backend.main.run_migrations"),
        patch("backend.main.get_engine"),
    ):
        create_app()

    mock_cors.assert_not_called()
