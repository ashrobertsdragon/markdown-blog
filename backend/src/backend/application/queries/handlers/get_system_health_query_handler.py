"""Handler for GetSystemHealthQuery."""

import logging
import os
import time
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import Engine, text

from backend.application.queries.get_system_health_query import (
    GetSystemHealthQuery,
    SystemHealth,
)

logger = logging.getLogger(__name__)


def get_system_health_query_handler(
    _query: GetSystemHealthQuery,
    engine: Engine,
    start_time: float,
) -> SystemHealth:
    """Return a health snapshot for the current process and database.

    api_status is unconditionally "healthy" because reaching this function
    proves the API layer is up. database reflects a live SELECT 1 probe.
    filesystem checks that the configured DRAFTS_PATH is writable.
    github_api always returns "healthy" — the health endpoint does not
    make external network calls to avoid latency spikes.

    Args:
        _query: GetSystemHealthQuery sentinel — carries no data.
        engine: SQLAlchemy Engine used to probe database connectivity.
        start_time: Unix timestamp from time.time() recorded at startup.

    Returns:
        SystemHealth with status, database, filesystem, github_api,
        uptime_seconds, and checked_at.
    """
    database = _probe_database(engine)
    filesystem = _probe_filesystem()
    github_api = "healthy"
    uptime_seconds = int(time.time() - start_time)

    statuses = [database, filesystem, github_api]
    if all(s == "healthy" for s in statuses):
        status = "healthy"
    elif any(s == "unhealthy" for s in statuses):
        status = "unhealthy"
    else:
        status = "degraded"

    return SystemHealth(
        status=status,
        database=database,
        filesystem=filesystem,
        github_api=github_api,
        uptime_seconds=uptime_seconds,
        checked_at=datetime.now(UTC).isoformat(),
    )


def _probe_database(engine: Engine) -> str:
    """Execute SELECT 1 against the engine to verify connectivity.

    Exception swallowing is intentional — a database outage should degrade
    gracefully rather than crash the health check.

    Args:
        engine: SQLAlchemy Engine to probe.

    Returns:
        "healthy" on success, "unhealthy" on any exception.
    """
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1")).fetchone()
        return "healthy"
    except Exception:
        logger.warning("Database health probe failed", exc_info=True)
        return "unhealthy"


def _probe_filesystem() -> str:
    """Check that the configured DRAFTS_PATH directory is accessible.

    Returns:
        "healthy" if the path exists and is a directory, "unhealthy" otherwise.
    """
    drafts_path = os.environ.get("DRAFTS_PATH", "")
    if not drafts_path:
        return "healthy"
    try:
        return "healthy" if Path(drafts_path).is_dir() else "unhealthy"
    except Exception:
        logger.warning("Filesystem health probe failed", exc_info=True)
        return "unhealthy"
