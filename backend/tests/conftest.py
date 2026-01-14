"""Shared test fixtures."""

import pytest

from backend.config import DevDBSettings, TestDBSettings


def pytest_addoption(parser):
    parser.addoption(
        "--run-external",
        action="store_true",
        default=False,
        help="Run tests marked as external",
    )


def pytest_collection_modifyitems(config, items):
    if config.getoption("--run-external"):
        return

    skip_external = pytest.mark.skip(
        reason="Use --run-external to run external tests"
    )
    for item in items:
        if "external" in item.keywords:
            item.add_marker(skip_external)


@pytest.fixture
def clean_env(monkeypatch):
    """Clear all DB-related and Clerk environment variables."""
    for key in [
        "DB_NAME",
        "DB_USER",
        "DB_PASSWORD",
        "FLASK_ENV",
        "LOCAL_DB_NAME",
        "LOCAL_DB_USER",
        "LOCAL_DB_PASSWORD",
        "CPANEL_DB_NAME",
        "CPANEL_DB_USER",
        "CPANEL_DB_PASSWORD",
        "CLERK_PUBLISHABLE_KEY",
        "CLERK_SECRET_KEY",
    ]:
        monkeypatch.delenv(key, raising=False)
    return monkeypatch


@pytest.fixture
def dev_env(clean_env):
    """Fixture to initialize DevDBSettings environment variables."""
    clean_env.setenv("FLASK_ENV", "DEVELOPMENT")
    clean_env.setenv("LOCAL_DB_NAME", "test_db")
    clean_env.setenv("LOCAL_DB_USER", "test_user")
    clean_env.setenv("LOCAL_DB_PASSWORD", "test_password")
    return clean_env


@pytest.fixture
def dev_settings(dev_env) -> DevDBSettings:
    """Fixture to initialize DevDBSettings class."""
    return DevDBSettings()


@pytest.fixture
def test_env(clean_env):
    """Fixture to initialize DevDBSettings environment variables."""
    clean_env.setenv("FLASK_ENV", "TESTING")
    clean_env.setenv("LOCAL_DB_NAME", "test_db")
    clean_env.setenv("LOCAL_DB_USER", "test_user")
    clean_env.setenv("LOCAL_DB_PASSWORD", "test_password")
    clean_env.setenv("CLERK_PUBLISHABLE_KEY", "pk_test_fake_key_for_testing")
    clean_env.setenv("CLERK_SECRET_KEY", "sk_test_fake_secret_for_testing")
    return clean_env


@pytest.fixture
def test_settings(test_env) -> TestDBSettings:
    """Fixture to initialize DevDBSettings class."""
    return TestDBSettings()
