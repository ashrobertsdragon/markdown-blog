"""Flask application factory.

This module contains the Flask app initialization and configuration,
including SPA routing, CORS handling, and blueprint registration.
"""

import logging
import time
import traceback
from pathlib import Path
from urllib.parse import unquote

from flask import Flask, abort, jsonify, request, send_from_directory
from flask.wrappers import Response
from flask_cors import CORS
from werkzeug.exceptions import HTTPException
from werkzeug.wrappers import Response as WerkzeugResponse

from backend.api.routes import (
    admin_bp,
    admin_comments_bp,
    auth_bp,
    comments_bp,
    health_bp,
    images_bp,
    notifications_bp,  # noqa: F401 - used in create_app
    posts_bp,
    revisions_bp,
    test_bp,
    users_bp,
)
from backend.config import (
    FileSystemSettings,
    FlaskEnv,
    FlaskSettings,
)
from backend.exceptions import (
    AuthenticationError,
    AuthorizationError,
    RateLimitExceededError,
)
from backend.infrastructure.monitoring.error_logger import ErrorLogger
from backend.infrastructure.persistence.database import get_engine
from backend.infrastructure.persistence.migrations import run_migrations
from scripts.create_schema import create_schema

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
    app.config["APP_START_TIME"] = time.time()

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
        create_schema()
    elif flask_env == FlaskEnv.PRODUCTION:
        run_migrations(get_engine())

    app.register_blueprint(health_bp, url_prefix="/api")
    app.register_blueprint(auth_bp, url_prefix="/api/auth")
    app.register_blueprint(users_bp, url_prefix="/api/users")
    app.register_blueprint(posts_bp, url_prefix="/api/posts")
    app.register_blueprint(comments_bp, url_prefix="/api/posts")
    app.register_blueprint(images_bp, url_prefix="/api/posts")
    app.register_blueprint(revisions_bp, url_prefix="/api/posts")
    app.register_blueprint(admin_bp)
    app.register_blueprint(admin_comments_bp, url_prefix="/api/admin")
    app.register_blueprint(notifications_bp, url_prefix="/api")
    app.register_blueprint(test_bp, url_prefix="/api/test")

    @app.errorhandler(AuthenticationError)
    def handle_authentication_error(
        error: AuthenticationError,
    ) -> tuple[Response, int]:
        """Handle authentication failures with 401 response.

        Args:
            error: The caught AuthenticationError instance.

        Returns:
            JSON response with error message and 401 status code.
        """
        return jsonify({"error": str(error)}), 401

    @app.errorhandler(AuthorizationError)
    def handle_authorization_error(
        error: AuthorizationError,
    ) -> tuple[Response, int]:
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
        return jsonify(payload), 403

    @app.errorhandler(RateLimitExceededError)
    def handle_rate_limit_exceeded_error(
        error: RateLimitExceededError,
    ) -> tuple[Response, int]:
        """Handle rate limit violations with 429 response.

        Args:
            error: The caught RateLimitExceededError instance.

        Returns:
            JSON response with error message and 429 status code, including
            X-RateLimit-Remaining and X-RateLimit-Reset headers.
        """
        response = jsonify(
            {
                "error": error.message,
                "code": "rate_limit_exceeded",
                "retry_after": int(error.reset_after),
            }
        )
        response.headers["X-RateLimit-Remaining"] = str(int(error.remaining))
        response.headers["X-RateLimit-Reset"] = str(
            int(time.time()) + int(error.reset_after)
        )
        return response, 429

    @app.errorhandler(Exception)
    def handle_unexpected_error(
        error: Exception,
    ) -> tuple[Response, int] | WerkzeugResponse:
        """Handle unexpected exceptions with generic 500 response.

        Logs detailed error information for debugging while returning
        a generic message to clients to prevent information disclosure.

        Flask's built-in HTTP exceptions (400, 404, 415, etc.) are
        returned with their native response to preserve proper status codes.

        Args:
            error: The caught Exception instance.

        Returns:
            WerkzeugResponse: For HTTPException, the exception's native
                response.
            tuple[Response, int]: For other exceptions, JSON error
                with 500 status.
        """
        if isinstance(error, HTTPException):
            return error.get_response()

        stack_trace = traceback.format_exc()
        endpoint = request.endpoint or request.path
        ErrorLogger.log_error(
            message=str(error),
            stack_trace=stack_trace,
            endpoint=endpoint,
        )

        logger.exception(
            "Unexpected error occurred",
            exc_info=error,
            extra={
                "error_type": type(error).__name__,
                "error_message": str(error),
            },
        )
        return jsonify({"error": "Internal server error"}), 500

    @app.errorhandler(404)
    def handle_not_found(_error: HTTPException) -> tuple[Response, int]:
        """Handle 404 Not Found errors, logging them to ErrorLogger.

        Args:
            _error: The caught HTTPException instance for the 404 error.

        Returns:
            JSON response with error message and 404 status code.
        """
        ErrorLogger.log_error(
            message=f"Not Found: {request.path}",
            stack_trace=str(_error.description) if _error.description else "",
            endpoint=request.endpoint or request.path,
        )
        return jsonify({"error": "Not found"}), 404

    _fs_settings = FileSystemSettings()
    _uploads_path = _fs_settings.UPLOADS_PATH

    @app.route("/uploads/<path:filepath>")
    def serve_upload(filepath: str) -> Response:
        """Serve an uploaded image with path traversal protection.

        Args:
            filepath: Relative path within UPLOADS_PATH
                (e.g. ``slug/photo.jpg``).

        Returns:
            File response with long-lived Cache-Control header.

        Raises:
            403: If the resolved path escapes UPLOADS_PATH.
        """
        uploads_root = _uploads_path.resolve()
        resolved = (_uploads_path / filepath).resolve()
        try:
            resolved.relative_to(uploads_root)
        except ValueError:
            abort(403)
        if not resolved.is_file():
            abort(404)
        response: Response = send_from_directory(_uploads_path, filepath)
        response.headers["Cache-Control"] = "public, max-age=31536000"
        return response

    @app.route("/tos")
    def serve_tos() -> Response | tuple[Response, int]:
        """Serve the Terms of Service plain text file.

        Returns:
            Plain text TOS file with a one-day cache header, or a 404 JSON
            response if the file is absent from the build directory.
        """
        file_path = build_dir / "tos"
        if not file_path.is_file():
            return jsonify({"error": "Terms of Service not found"}), 404
        response = send_from_directory(
            str(build_dir), "tos", mimetype="text/plain; charset=utf-8"
        )
        response.headers["Cache-Control"] = "public, max-age=86400"
        return response

    @app.route("/privacy")
    def serve_privacy() -> Response | tuple[Response, int]:
        """Serve the Privacy Policy plain text file.

        Returns:
            Plain text Privacy Policy file with a one-day cache header, or a
            404 JSON response if the file is absent from the build directory.
        """
        file_path = build_dir / "privacy"
        if not file_path.is_file():
            return jsonify({"error": "Privacy Policy not found"}), 404
        response = send_from_directory(
            str(build_dir), "privacy", mimetype="text/plain; charset=utf-8"
        )
        response.headers["Cache-Control"] = "public, max-age=86400"
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
            abort(404)

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
