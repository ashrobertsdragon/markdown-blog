"""Passenger WSGI entry point for cPanel deployment.

This module serves as the WSGI entry point for Passenger web server on cPanel
shared hosting. It handles virtual environment bootstrap and Flask application
initialization.

Environment Variables:
    VENV_PATH: Path to Python virtual environment (uv-managed).

Deployment Notes:
    - Passenger requires the WSGI application object to be named 'application'
    - Dependencies must be synced: `uv sync`
    - This file should be placed in the application root directory
    - Passenger will execute this file to start the application

Usage:
    Passenger automatically loads this module when starting the application.
    No manual execution required in production.

References:
    - PEP 3333: Python Web Server Gateway Interface v1.0.1
    - Passenger documentation: https://www.phusionpassenger.com/
"""

import os
import sys

APP_ROOT = os.path.dirname(os.path.abspath(__file__))
if APP_ROOT not in sys.path:
    sys.path.insert(0, APP_ROOT)


def ensure_virtualenv(path: str | None = None) -> None:
    """Ensure we are running inside the configured virtual environment.

    Args:
        path: Optional override for virtual environment path.
    """
    venv_path = path or os.environ.get("VENV_PATH")
    if not venv_path:
        raise ValueError("Virtual Environment path must be set")

    if sys.platform == "win32":
        python_bin = os.path.join(venv_path, "Scripts", "python.exe")
    else:
        python_bin = os.path.join(venv_path, "bin", "python3")

    if sys.executable != python_bin and os.path.exists(python_bin):
        os.execl(python_bin, python_bin, *sys.argv)


if os.environ.get("FLASK_ENV") != "TESTING":
    ensure_virtualenv()

from backend.main import create_app  # noqa: E402

application = create_app()
