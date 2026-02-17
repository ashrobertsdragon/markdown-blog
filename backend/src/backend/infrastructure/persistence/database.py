"""Database connection management with SQLModel.

Provides PostgreSQL connection management using SQLModel with connection
pooling, health checks, and session lifecycle management for dependency
injection.
"""

from collections.abc import Generator

from sqlalchemy.engine import Engine
from sqlmodel import Session, create_engine

_engine: Engine | None = None


def get_engine() -> Engine:
    """Get or create database engine.

    Returns:
        SQLAlchemy Engine instance.
    """
    global _engine
    if _engine is None:
        from backend.config import _db_settings

        settings = _db_settings()
        _engine = create_engine(
            settings.url,
            pool_pre_ping=True,
            echo=False,
            **settings.engine_kwargs,
        )
    return _engine


def get_db() -> Generator[Session]:
    """Context manager for database sessions.

    Yields:
        SQLModel Session instance
    """
    with Session(get_engine()) as session:
        yield session


def dispose_engine() -> None:
    """Dispose of the cached database engine and clear cache.

    Useful for tests to ensure connections are closed and resources freed.
    """
    global _engine
    if _engine is not None:
        _engine.dispose()
        _engine = None
