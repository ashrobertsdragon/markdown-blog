"""Shared test fixtures."""

import datetime
import sqlite3

import pytest

from backend.config import (
    DevDBSettings,
    TestDBSettings,
    _db_settings,
    get_db_url,
)
from backend.infrastructure.persistence.database import (
    dispose_engine,
    get_engine,
)
from backend.infrastructure.persistence.models import SQLModel
from backend.main import create_app


@pytest.fixture(autouse=True)
def register_adapters() -> None:
    sqlite3.register_adapter(datetime.datetime, lambda v: v.isoformat())
    sqlite3.register_adapter(datetime.date, lambda v: v.isoformat())
    sqlite3.register_converter(
        "datetime", lambda v: datetime.datetime.fromisoformat(v.decode())
    )
    sqlite3.register_converter(
        "date", lambda v: datetime.date.fromisoformat(v.decode())
    )


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
    clean_env.setenv("GITHUB_PERSONAL_ACCESS_TOKEN", "test_token_for_testing")
    clean_env.setenv("RESEND_API_KEY", "re_test_fake_key_for_testing")
    return clean_env


@pytest.fixture
def test_settings(test_env) -> TestDBSettings:
    """Fixture to initialize DevDBSettings class."""
    return TestDBSettings()


@pytest.fixture
def test_build_dir(tmp_path):
    """Create real test build directory without overwriting production files."""
    build_dir = tmp_path / "build"
    static_dir = build_dir / "static"
    js_dir = static_dir / "js"

    build_dir.mkdir()
    static_dir.mkdir()
    js_dir.mkdir()

    index_html = build_dir / "index.html"
    index_html.write_text("<html><body><div id='root'></div></body></html>")

    (build_dir / "favicon.ico").write_bytes(b"fake-icon")
    (build_dir / "manifest.json").write_text('{"name": "test"}')

    test_js = js_dir / "main.abc123.js"
    test_js.write_text("console.log('test');")

    yield build_dir


@pytest.fixture
def client(test_settings, test_build_dir, monkeypatch, tmp_path):
    monkeypatch.setenv("BUILD_DIR", str(test_build_dir))
    monkeypatch.setenv("DRAFTS_PATH", str(tmp_path / "drafts"))
    monkeypatch.setenv("GITHUB_PERSONAL_ACCESS_TOKEN", "test_token")
    monkeypatch.setenv("GITHUB_OWNER", "test_owner")
    monkeypatch.setenv("GITHUB_REPO", "test_repo")

    import backend.api.dependencies
    import backend.api.routes.comments
    import backend.api.routes.posts

    monkeypatch.setattr(backend.api.routes.posts, "_filesystem_settings", None)
    monkeypatch.setattr(backend.api.routes.posts, "_github_settings", None)
    monkeypatch.setattr(backend.api.dependencies, "_github_service", None)
    monkeypatch.setattr(backend.api.routes.comments, "_post_repository", None)
    monkeypatch.setattr(
        backend.api.routes.comments, "_comment_repository", None
    )
    monkeypatch.setattr(
        backend.api.routes.comments, "_rate_limit_service", None
    )
    monkeypatch.setattr(
        backend.api.routes.comments, "_spam_check_service", None
    )

    app = create_app()

    engine = get_engine()
    SQLModel.metadata.create_all(engine)

    return app.test_client()


@pytest.fixture(autouse=True)
def dispose_engine_after_test():
    """Ensure engine is disposed after every test to free resources."""
    yield

    _db_settings.cache_clear()
    get_db_url.cache_clear()
    dispose_engine()


def pytest_sessionfinish(session, exitstatus):
    """Clean up resources after all tests in the session have run."""

    _db_settings.cache_clear()
    get_db_url.cache_clear()
    dispose_engine()
