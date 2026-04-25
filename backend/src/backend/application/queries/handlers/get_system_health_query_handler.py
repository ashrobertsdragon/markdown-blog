"""Handler for GetSystemHealthQuery."""

import logging
import time

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
    proves the API layer is up. database_status reflects a live SELECT 1
    probe; any exception is swallowed intentionally so a degraded database
    never prevents the health endpoint from responding. uptime is derived
    from the application-level start_time captured at process startup.

    Args:
        _query: GetSystemHealthQuery sentinel — carries no data.
        engine: SQLAlchemy Engine used to probe database connectivity.
        start_time: Unix timestamp from time.time() recorded at startup.

    Returns:
        SystemHealth with api_status, database_status, and uptime.
    """
    database_status = _probe_database(engine)
    uptime = int(time.time() - start_time)
    return SystemHealth(
        api_status="healthy",
        database_status=database_status,
        uptime=uptime,
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
            conn.execute(text("SELECT 1"))
        return "healthy"
    except Exception:
        logger.warning("Database health probe failed", exc_info=True)
        return "unhealthy"
