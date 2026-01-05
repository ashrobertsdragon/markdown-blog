"""End-to-end integration test for production build.

Tests the complete production stack:
- Frontend production build
- Flask serving React static files
- Health check endpoints
- SPA routing in browser
"""

import shutil
import subprocess
import threading
from pathlib import Path, WindowsPath

import pytest
import requests
from pytest import MonkeyPatch

from backend.main import create_app
from tests.e2e.utils import wait_for_server

PROJECT_ROOT = Path(__file__).parents[3]
BUILD_DIR = PROJECT_ROOT / "build"
BASE_URL = "http://localhost:5000"


@pytest.fixture(scope="module")
def build():
    build_dir_preexists = BUILD_DIR.exists()

    script_path = (PROJECT_ROOT / "scripts" / "build.sh").absolute()
    script = str(script_path)
    command = f'chmod +x "{script}" && "{script}"'

    if isinstance(PROJECT_ROOT, WindowsPath):
        letter = PROJECT_ROOT.drive[0].lower()
        cyg_path = "/" + letter + script_path.as_posix()[2:]
        wsl_path = "/mnt" + cyg_path
        command = (
            f'"{cyg_path}" 2>/dev/null || "{wsl_path}" 2>/dev/null || exit 1'
        )

    cmd = ["bash", "-c", command]
    result = subprocess.run(cmd, text=True, capture_output=True)
    if result.returncode != 0:
        pytest.exit(
            f"Failed to build frontend: \n{result.stdout}\n{result.stderr}"
        )

    try:
        yield
    finally:
        if not build_dir_preexists:
            shutil.rmtree(BUILD_DIR, ignore_errors=True)


@pytest.fixture(scope="module")
def flask_server(build):
    """Start Flask server for e2e testing."""
    monkeypatch = MonkeyPatch()
    monkeypatch.setenv("FLASK_ENV", "PRODUCTION")
    app = create_app()
    thread = threading.Thread(
        target=app.run,
        kwargs={
            "host": "localhost",
            "port": 5000,
            "debug": False,
            "use_reloader": False,
        },
        daemon=True,
    )
    thread.start()
    try:
        wait_for_server(f"{BASE_URL}/health")
        yield
    finally:
        monkeypatch.undo()


def test_frontend_build_creates_static_assets(flask_server):
    """Verify production build creates required static assets."""
    assert (BUILD_DIR / "index.html").exists()
    assert (BUILD_DIR / "static").exists()


def test_health_endpoint_responds(flask_server):
    """Verify GET /health returns 200 OK."""
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=1)
        assert response.status_code == 200
        assert response.json() == {"status": "healthy"}
    except requests.exceptions.RequestException:
        pytest.fail("Flask server failed to start")


def test_health_db_endpoint_responds(flask_server):
    """Verify GET /health/db returns 200 OK."""
    response = requests.get(f"{BASE_URL}/health/db", timeout=5)

    assert response.status_code in {200, 503}


@pytest.mark.external
def test_health_github_endpoint_responds(flask_server):
    """Verify GET /health/github returns appropriate status.

    Note: This test requires network access to GitHub. Marked as external
    to allow skipping in offline or restricted environments.
    """
    response = requests.get(f"{BASE_URL}/health/github", timeout=10)

    assert response.status_code in {200, 503}


def test_root_path_serves_react_index(flask_server):
    """Verify GET / serves React index.html."""
    response = requests.get(BASE_URL, timeout=5)

    assert response.status_code == 200
    assert "<!doctype html>" in response.text.lower()
    assert '<div id="root"></div>' in response.text


def test_invalid_route_serves_react_index(flask_server):
    """Verify unknown routes serve React index.html for client-side routing."""
    response = requests.get(f"{BASE_URL}/invalid-route", timeout=5)

    assert response.status_code == 200
    assert "<!doctype html>" in response.text.lower()
    assert '<div id="root"></div>' in response.text


def test_api_routes_not_caught_by_spa_catchall(flask_server):
    """Verify /api/* routes are not caught by SPA catch-all."""
    response = requests.get(f"{BASE_URL}/api/nonexistent", timeout=5)

    assert response.status_code == 404
