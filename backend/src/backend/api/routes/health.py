"""Health check endpoints for application and dependency monitoring.

Provides endpoints to check application uptime, database connectivity,
and GitHub API reachability.
"""

import logging

import requests
from flask import Blueprint, Response, jsonify
from sqlalchemy import text

from backend.infrastructure.persistence.database import get_engine

logger = logging.getLogger(__name__)

health_bp = Blueprint("health", __name__)


@health_bp.route("/health", methods=["GET"])
def health() -> tuple[Response, int]:
    """Basic uptime health check.

    Returns:
        JSON response with healthy status and 200 OK.
    """
    return jsonify({"status": "healthy"}), 200


@health_bp.route("/health/db", methods=["GET"])
def health_db() -> tuple[Response, int]:
    """Database connectivity health check.

    Tests PostgreSQL connection by executing SELECT 1 query.

    Returns:
        JSON response with database status.
        - 200 OK if database is reachable
        - 503 Service Unavailable if database connection fails
    """
    try:
        with get_engine().connect() as conn:
            conn.execute(text("SELECT 1"))
        return jsonify({"status": "healthy", "database": "connected"}), 200
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        return (
            jsonify({"status": "unhealthy", "database": "unreachable"}),
            503,
        )


@health_bp.route("/health/github", methods=["GET"])
def health_github() -> tuple[Response, int]:
    """GitHub API reachability health check.

    Tests connectivity to GitHub API by calling rate_limit endpoint.

    Returns:
        JSON response with GitHub API status.
        - 200 OK if GitHub API is reachable
        - 503 Service Unavailable if GitHub API is unreachable
    """
    try:
        response = requests.get("https://api.github.com/rate_limit", timeout=5)
        response.raise_for_status()
        return jsonify({"status": "healthy", "github": "reachable"}), 200
    except requests.exceptions.RequestException as e:
        logger.error(f"GitHub API health check failed: {e}")
        return (
            jsonify({"status": "unhealthy", "github": "unreachable"}),
            503,
        )
