import os
import sys
from unittest.mock import patch

import pytest


@pytest.fixture
def ensure_virtualenv(monkeypatch):
    """Fixture to safely import and provide ensure_virtualenv function."""
    monkeypatch.setenv("FLASK_ENV", "TESTING")
    from passenger_wsgi import ensure_virtualenv

    return ensure_virtualenv


@pytest.fixture
def mock_virtualenv() -> str:
    """Fixture providing a mock virtual environment path."""
    return os.path.join("home", "cpaneluser", "virtualenv", "blog")


def test_ensure_virtualenv_raises_without_path(ensure_virtualenv, monkeypatch):
    """ensure_virtualenv should raise ValueError when no path/envvar set."""
    monkeypatch.delenv("VENV_PATH", raising=False)
    with pytest.raises(
        ValueError, match="Virtual Environment path must be set"
    ):
        ensure_virtualenv()


@pytest.mark.parametrize("flask_env", ["development", "production", None])
def test_passenger_wsgi_raises_value_error(flask_env, monkeypatch):
    """passenger_wsgi should raise ValueError when flask_env not 'testing'."""
    if flask_env is not None:
        monkeypatch.setenv("FLASK_ENV", flask_env)
    else:
        monkeypatch.delenv("FLASK_ENV", raising=False)
    monkeypatch.delenv("VENV_PATH", raising=False)

    if "passenger_wsgi" in sys.modules:
        del sys.modules["passenger_wsgi"]

    with pytest.raises(
        ValueError, match="Virtual Environment path must be set"
    ):
        import passenger_wsgi


def test_passenger_wsgi_testing_does_not_exec(monkeypatch):
    """passenger_wsgi should not call os.execl when FLASK_ENV is TESTING."""
    monkeypatch.setenv("FLASK_ENV", "TESTING")
    monkeypatch.delenv("VENV_PATH", raising=False)

    if "passenger_wsgi" in sys.modules:
        del sys.modules["passenger_wsgi"]
    with patch("os.execl") as mock_execl:
        mock_execl.assert_not_called()


def test_ensure_virtualenv_unix_path(
    ensure_virtualenv, mock_virtualenv, monkeypatch
):
    """Test path resolution on Unix-like systems."""
    monkeypatch.setattr(sys, "platform", "linux")
    monkeypatch.setenv("VENV_PATH", mock_virtualenv)

    expected_python = os.path.join(mock_virtualenv, "bin", "python3")

    with (
        patch("sys.executable", "different/path"),
        patch("os.path.exists", return_value=True),
        patch("os.execl") as mock_execl,
    ):
        ensure_virtualenv()
        mock_execl.assert_called_once()
        args = mock_execl.call_args[0]
        assert args[0] == expected_python
        assert args[1] == expected_python


def test_ensure_virtualenv_windows_path(
    ensure_virtualenv, mock_virtualenv, monkeypatch
):
    """Test path resolution on Windows systems."""
    monkeypatch.setattr(sys, "platform", "win32")
    monkeypatch.setenv("VENV_PATH", mock_virtualenv)

    expected_python = os.path.join(mock_virtualenv, "Scripts", "python.exe")

    with (
        patch("sys.executable", "different/path"),
        patch("os.path.exists", return_value=True),
        patch("os.execl") as mock_execl,
    ):
        ensure_virtualenv()
        mock_execl.assert_called_once()
        args = mock_execl.call_args[0]
        assert args[0] == expected_python


def test_ensure_virtualenv_no_exec_if_already_active(
    ensure_virtualenv, mock_virtualenv, monkeypatch
):
    """Test that os.execl is NOT called if we are already in the venv."""
    monkeypatch.setattr(sys, "platform", "linux")
    monkeypatch.setenv("VENV_PATH", mock_virtualenv)

    expected_python = os.path.join(mock_virtualenv, "bin", "python3")

    with (
        patch("sys.executable", expected_python),
        patch("os.path.exists", return_value=True),
        patch("os.execl") as mock_execl,
    ):
        ensure_virtualenv()
        mock_execl.assert_not_called()
