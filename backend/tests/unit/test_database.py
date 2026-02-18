"""Unit tests for database connection management.

Tests SQLModel engine initialization, connection pooling, and session
lifecycle management.
"""

import pytest
from sqlalchemy.engine import Engine
from sqlmodel import Session

from backend.infrastructure.persistence.database import (
    dispose_engine,
    get_db,
    get_engine,
)


@pytest.fixture
def engine(dev_settings):
    """Fixture to clear get_engine cache and return Engine."""
    dispose_engine()
    return get_engine()


def test_get_engine_returns_engine(engine):
    """get_engine should return SQLModel engine instance."""
    assert isinstance(engine, Engine)


def test_engine_uses_postgresql(engine):
    """Engine should be configured for PostgreSQL."""
    assert "postgresql" in str(engine.url)


def test_engine_uses_localhost(engine):
    """Engine should use localhost for DB_HOST (cPanel requirement)."""
    assert engine.url.host == "localhost"


def test_engine_has_pool_pre_ping(engine):
    """Engine should configure pool_pre_ping for health checks."""
    assert engine.pool._pre_ping is True


def test_get_engine_is_cached(engine):
    """get_engine should return same instance on repeated calls."""
    dispose_engine()
    engine1 = get_engine()
    engine2 = get_engine()
    assert engine1 is engine2


def test_get_db_yields_session(engine):
    """get_db should yield SQLModel Session instance."""
    db_gen = get_db()
    session = next(db_gen)

    assert isinstance(session, Session)


def test_multiple_get_db_calls_yield_different_sessions(engine):
    """Multiple calls to get_db should yield independent sessions."""
    db_gen1 = get_db()
    db_gen2 = get_db()

    session1 = next(db_gen1)
    session2 = next(db_gen2)

    assert session1 is not session2
