"""e2e tests for database connection management."""

import os

import pytest
from sqlmodel import select

from backend.infrastructure.persistence.database import get_db


@pytest.mark.skipif(
    not os.environ.get("DB_NAME")
    and os.environ.get("FLASK_ENV", "").upper() != "TESTING",
    reason="Database not configured",
)
def test_session_can_execute_simple_query():
    """Session from get_db should execute SELECT queries."""
    db_gen = get_db()
    session = next(db_gen)

    result = session.exec(select(1)).one()
    assert result == 1
