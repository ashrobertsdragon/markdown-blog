"""Shared fixtures for integration tests."""

import pytest

from backend.main import create_app


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
    """Create Flask test client with real test build directory."""
    monkeypatch.setenv("BUILD_DIR", str(test_build_dir))
    monkeypatch.setenv("DRAFTS_PATH", str(tmp_path / "drafts"))
    monkeypatch.setenv("GITHUB_PERSONAL_ACCESS_TOKEN", "test_token")
    monkeypatch.setenv("GITHUB_OWNER", "test_owner")
    monkeypatch.setenv("GITHUB_REPO", "test_repo")
    app = create_app()
    return app.test_client()
