"""Unit tests for GetSystemHealthQuery, SystemHealth, and get_system_health_query_handler.

Test Coverage:
- GetSystemHealthQuery is a frozen dataclass with no parameters (1 test)
- SystemHealth stores all required fields and is immutable (1 test)
- Handler returns healthy status when database is reachable (1 test)
- Handler returns unhealthy database when connection fails (1 test)
- Handler returns unhealthy when execute raises after connect succeeds (1 test)
- Handler status is always 'healthy' when all subsystems are up (1 test)
- Handler calculates uptime correctly from start_time (1 test)

Total: 7 unit tests
"""

import time
from unittest.mock import MagicMock, patch

import pytest

from backend.application.queries.get_system_health_query import (
    GetSystemHealthQuery,
    SystemHealth,
)
from backend.application.queries.handlers.get_system_health_query_handler import (
    get_system_health_query_handler,
)


def test_get_system_health_query_is_frozen_dataclass() -> None:
    """Verify GetSystemHealthQuery is a frozen dataclass with no parameters.

    The query acts as a sentinel value object — it carries no input
    and must be immutable so it cannot be modified after creation.
    """
    query = GetSystemHealthQuery()

    with pytest.raises((AttributeError, TypeError)):
        query.anything = "value"  # type: ignore[attr-defined]


def test_system_health_frozen_dataclass() -> None:
    """Verify SystemHealth stores all required fields and is immutable.

    The result dataclass must hold status, database, filesystem, github_api,
    uptime_seconds, and checked_at so callers can read the full snapshot.
    """
    health = SystemHealth(
        status="healthy",
        database="healthy",
        filesystem="healthy",
        github_api="healthy",
        uptime_seconds=120,
        checked_at="2026-01-01T00:00:00+00:00",
    )

    assert health.status == "healthy"
    assert health.database == "healthy"
    assert health.filesystem == "healthy"
    assert health.github_api == "healthy"
    assert health.uptime_seconds == 120
    assert health.checked_at == "2026-01-01T00:00:00+00:00"

    with pytest.raises((AttributeError, TypeError)):
        health.status = "degraded"  # type: ignore[misc]


def test_handle_returns_healthy_when_database_up() -> None:
    """Verify handler returns healthy statuses when the database is reachable.

    When engine.connect() succeeds and SELECT 1 executes without error,
    both status and database must be 'healthy', and uptime_seconds
    must be a non-negative integer.
    """
    mock_engine = MagicMock()
    mock_conn = MagicMock()
    mock_engine.connect.return_value.__enter__ = MagicMock(
        return_value=mock_conn
    )
    mock_engine.connect.return_value.__exit__ = MagicMock(return_value=False)

    start_time = time.time()
    with patch.dict("os.environ", {"DRAFTS_PATH": "/tmp"}):
        result = get_system_health_query_handler(
            GetSystemHealthQuery(), engine=mock_engine, start_time=start_time
        )

    assert isinstance(result, SystemHealth)
    assert result.status == "healthy"
    assert result.database == "healthy"
    assert isinstance(result.uptime_seconds, int)
    assert result.uptime_seconds >= 0


def test_handle_returns_unhealthy_database_when_connection_fails() -> None:
    """Verify handler sets database to 'unhealthy' on connection failure.

    When engine.connect() raises an exception, the database is unreachable.
    The handler must catch the exception and return database='unhealthy'
    rather than propagating the error to the caller.
    """
    mock_engine = MagicMock()
    mock_engine.connect.side_effect = Exception("connection refused")

    result = get_system_health_query_handler(
        GetSystemHealthQuery(), engine=mock_engine, start_time=time.time()
    )

    assert result.database == "unhealthy"


def test_handle_returns_unhealthy_when_execute_fails() -> None:
    """Verify handler sets database to 'unhealthy' when execute raises.

    When engine.connect() succeeds but conn.execute() raises an exception
    (e.g., a permission error or query timeout), the handler must still
    catch the exception and return database='unhealthy'.
    """
    mock_engine = MagicMock()
    mock_conn = MagicMock()
    mock_conn.execute.side_effect = Exception("permission denied")
    mock_engine.connect.return_value.__enter__ = MagicMock(
        return_value=mock_conn
    )
    mock_engine.connect.return_value.__exit__ = MagicMock(return_value=False)

    result = get_system_health_query_handler(
        GetSystemHealthQuery(), engine=mock_engine, start_time=time.time()
    )

    assert result.database == "unhealthy"


def test_handle_api_status_always_healthy() -> None:
    """Verify status is 'healthy' when all subsystems including database are up.

    The handler was reached, which proves the API layer is operational.
    When database, filesystem, and github_api are all healthy, status is healthy.
    """
    mock_engine = MagicMock()
    mock_conn = MagicMock()
    mock_engine.connect.return_value.__enter__ = MagicMock(
        return_value=mock_conn
    )
    mock_engine.connect.return_value.__exit__ = MagicMock(return_value=False)

    start_time = time.time()
    with patch.dict("os.environ", {"DRAFTS_PATH": "/tmp"}):
        result_db_up = get_system_health_query_handler(
            GetSystemHealthQuery(),
            engine=mock_engine,
            start_time=start_time,
        )

    assert result_db_up.status == "healthy"
    assert result_db_up.github_api == "healthy"


def test_handle_calculates_uptime_correctly() -> None:
    """Verify handler computes uptime as int(time.time() - start_time).

    Given a start_time 100 seconds in the past, uptime_seconds must equal 100
    within a ±1 second tolerance to account for execution time jitter.
    """
    mock_engine = MagicMock()
    mock_conn = MagicMock()
    mock_engine.connect.return_value.__enter__ = MagicMock(
        return_value=mock_conn
    )
    mock_engine.connect.return_value.__exit__ = MagicMock(return_value=False)

    now = time.time()
    start_time = now - 100

    with patch("time.time", return_value=now):
        result = get_system_health_query_handler(
            GetSystemHealthQuery(), engine=mock_engine, start_time=start_time
        )

    assert abs(result.uptime_seconds - 100) <= 1
