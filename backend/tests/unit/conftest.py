"""Shared test fixtures for all database settings."""

from collections.abc import Generator
from unittest.mock import MagicMock, patch

import pytest

from backend.config import DBSettings, ProductionDBSettings


@pytest.fixture
def valid_env(clean_env):
    """Fixture to set environment variables."""
    clean_env.setenv("DB_NAME", "blog_db")
    clean_env.setenv("DB_USER", "blog_user")
    clean_env.setenv("DB_PASSWORD", "secure_password")
    return clean_env


@pytest.fixture
def base_settings(valid_env) -> DBSettings:
    """Fixture to initialize base DBSettings class."""
    return DBSettings()


@pytest.fixture
def production_env(clean_env):
    """Fixture to initialize ProductionDBSettings environment variables."""
    clean_env.setenv("FLASK_ENV", "PRODUCTION")
    clean_env.setenv("DB_NAME", "PRODUCTION_DB")
    clean_env.setenv("DB_USER", "PRODUCTION_USER")
    clean_env.setenv("DB_PASSWORD", "PRODUCTION_PASSWORD")
    return clean_env


@pytest.fixture
def production_settings(production_env) -> ProductionDBSettings:
    """Fixture to initialize ProductionDBSettings class."""
    return ProductionDBSettings()


@pytest.fixture(autouse=True)
def clear_error_logger_after_test() -> Generator[None]:
    """Ensure ErrorLogger state is clean before and after each unit test.

    Autouse is required here because ErrorLogger holds class-level state in a
    module-scoped deque. Without explicit cleanup, entries logged in one test
    would bleed into the next, making ordering and count assertions unreliable.
    """
    from backend.infrastructure.monitoring.error_logger import ErrorLogger

    ErrorLogger.clear()
    yield
    ErrorLogger.clear()


@pytest.fixture
def mock_logger() -> Generator[MagicMock]:
    """Mock the Python logger inside ErrorLogger.

    Patches the module-level logger so tests can assert that log_error()
    delegates to the standard logging machinery without inspecting real log
    output.
    """
    with patch(
        "backend.infrastructure.monitoring.error_logger.logger"
    ) as mocked:
        yield mocked


@pytest.fixture
def sample_error_entry():
    """Return a pre-built ErrorEntry with deterministic field values.

    Provides a ready-made instance for tests that need an ErrorEntry but are
    not testing construction itself.
    """
    from datetime import UTC, datetime

    from backend.infrastructure.monitoring.error_logger import ErrorEntry

    return ErrorEntry(
        timestamp=datetime(2024, 1, 1, 12, 0, 0, tzinfo=UTC),
        message="sample error message",
        stack_trace="Traceback (most recent call last):\n  File 'app.py', line 1\nRuntimeError: sample",
        endpoint="/api/posts",
    )
