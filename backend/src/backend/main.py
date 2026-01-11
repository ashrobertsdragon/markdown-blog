"""Flask application factory.

This module contains the Flask app initialization and configuration,
including SPA routing, CORS handling, and blueprint registration.
"""

import logging
from pathlib import Path
from urllib.parse import unquote

from flask import Flask, Response, jsonify, send_from_directory
from flask_cors import CORS

from backend.api.routes.health import health_bp
from backend.config import FlaskEnv, FlaskSettings
from backend.exceptions import AuthenticationError, AuthorizationError

logger = logging.getLogger(__name__)


def create_app() -> Flask:
    """Create and configure the Flask application.

    Returns:
        Configured Flask application instance.

    Raises:
        RuntimeError: If build directory is missing in production environment.
    """
    settings = FlaskSettings()
    flask_env: FlaskEnv = settings.FLASK_ENV
    build_dir: Path = settings.BUILD_DIR
    static_dir: str = settings.STATIC_DIR

    app = Flask(
        __name__,
        static_folder=static_dir,
        static_url_path="/static",
        template_folder=str(build_dir),
    )

    if not build_dir.exists():
        if flask_env == FlaskEnv.PRODUCTION:
            raise RuntimeError(
                "Frontend build directory not found. Run 'npm run build' first."
            )
        logger.warning(
            "Frontend build directory not found. SPA routes will return 503."
        )

    if flask_env in [FlaskEnv.TESTING, FlaskEnv.DEVELOPMENT]:
        CORS(app)

    app.register_blueprint(health_bp, url_prefix="")

    @app.errorhandler(AuthenticationError)
    def handle_authentication_error(error: AuthenticationError) -> Response:
        """Handle authentication failures with 401 response.

        Args:
            error: The caught AuthenticationError instance.

        Returns:
            JSON response with error message and 401 status code.
        """
        response = jsonify({"error": str(error)})
        response.status_code = 401
        return response

    @app.errorhandler(AuthorizationError)
    def handle_authorization_error(error: AuthorizationError) -> Response:
        """Handle authorization failures with 403 response.

        Args:
            error: The caught AuthorizationError instance.

        Returns:
            JSON response with error message, optional required_role,
            and 403 status code.
        """
        payload = {"error": error.message}
        if error.required_role is not None:
            payload["required_role"] = error.required_role
        response = jsonify(payload)
        response.status_code = 403
        return response

    @app.route("/", defaults={"path": ""})
    @app.route("/<path:path>")
    def serve_spa(path: str) -> Response | tuple[Response, int]:
        r"""Serve React SPA for all non-API routes.

        Args:
            path: The requested URL path.

        Returns:
            - 400 with error JSON if path contains ".." or "\\"
            - 404 with error JSON if path starts with "api/"
            - 200 with file if path matches existing file in build_dir
            - 200 with index.html for SPA routes (default)
            - 503 with error JSON if index.html doesn't exist

        Raises:
            None (all exceptions handled internally)
        """
        decoded_path = unquote(unquote(path))
        if ".." in decoded_path or "\\" in decoded_path:
            logger.warning(f"Path traversal attempt blocked: {path}")
            return jsonify({"error": "Invalid path"}), 400

        if path.startswith("api/"):
            return jsonify({"error": "Not found"}), 404

        path = path or "index.html"
        file_path = build_dir / path

        try:
            if file_path.is_file():
                return send_from_directory(str(build_dir), path)
        except (OSError, ValueError) as e:
            logger.debug(f"File access error for path '{path}': {e}")

        index_path = build_dir / "index.html"
        try:
            if index_path.is_file():
                return send_from_directory(str(build_dir), "index.html")
        except (OSError, ValueError) as e:
            logger.debug(f"Index.html access error: {e}")

        return jsonify({"error": "Service unavailable"}), 503

    return app
