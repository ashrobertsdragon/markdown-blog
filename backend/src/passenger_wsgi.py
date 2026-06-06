"""WSGI entry point for cPanel shared hosting (LiteSpeed lswsgi / Passenger).

This module is the WSGI entry point loaded by the web server on cPanel shared
hosting. On CloudLinux + LiteSpeed the application is launched by ``lswsgi``
using the Python Selector's virtualenv, so no virtualenv bootstrap is needed.
On stock Passenger hosts where ``VENV_PATH`` is provided, it re-executes under
that interpreter before importing the application.

Environment Variables:
    VENV_PATH: Optional path to the Python virtual environment. When set and
        valid, the process re-executes under that interpreter. When unset (the
        CloudLinux Python Selector case), the current interpreter is used.

Deployment Notes:
    - The WSGI application object must be named 'application'.
    - The 'backend' package sits beside this file in the application root, which
      is added to sys.path so it is importable.

References:
    - PEP 3333: Python Web Server Gateway Interface v1.0.1
"""

import os
import sys

APP_ROOT = os.path.dirname(os.path.abspath(__file__))
if APP_ROOT not in sys.path:
    sys.path.insert(0, APP_ROOT)


def ensure_virtualenv(path: str | None = None) -> None:
    """Re-execute under the configured virtualenv interpreter if one is set.

    Does nothing when no virtualenv path is configured, which is the expected
    case under the CloudLinux Python Selector where ``lswsgi`` already runs the
    selector-managed interpreter.

    Args:
        path: Optional override for the virtual environment path. Falls back to
            the ``VENV_PATH`` environment variable.
    """
    venv_path = path or os.environ.get("VENV_PATH")
    if not venv_path:
        return

    python_bin = os.path.join(venv_path, "bin", "python3")
    already_active = os.path.realpath(sys.executable) == os.path.realpath(
        python_bin
    )
    if not already_active and os.path.exists(python_bin):
        os.execl(python_bin, python_bin, *sys.argv)


if os.environ.get("FLASK_ENV") != "TESTING":
    ensure_virtualenv()

from backend.main import create_app  # noqa: E402

application = create_app()
