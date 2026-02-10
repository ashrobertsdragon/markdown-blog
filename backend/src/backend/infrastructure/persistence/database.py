"""Database connection management with SQLModel.

Provides PostgreSQL connection management using SQLModel with connection
pooling, health checks, and session lifecycle management for dependency
injection.
"""

from collections.abc import Generator
from functools import lru_cache

from sqlalchemy.engine import Engine
from sqlmodel import Session, create_engine


@lru_cache
def get_engine() -> Engine:
    """Get or create database engine."""
    from backend.config import _db_settings

    settings = _db_settings()
    return create_engine(
        settings.url,
        pool_pre_ping=True,
        echo=False,
        **settings.engine_kwargs,
    )


def get_db() -> Generator[Session]:
    """Context manager for database sessions.

    Yields:
        SQLModel Session instance
    """
    with Session(get_engine()) as session:
        yield session
