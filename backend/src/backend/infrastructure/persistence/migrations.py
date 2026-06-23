"""Idempotent startup schema migrations.

Runs DDL migrations that add missing columns to existing tables.
Each migration uses IF NOT EXISTS / conditional checks so it is safe
to re-run on every application startup.
"""

import logging

from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine

logger = logging.getLogger(__name__)


def run_migrations(engine: Engine) -> None:
    """Apply any pending schema migrations.

    Args:
        engine: SQLAlchemy engine connected to the target database.
    """
    inspector = inspect(engine)
    existing_columns = {col["name"] for col in inspector.get_columns("post")}
    if "html_content" not in existing_columns:
        with engine.connect() as conn:
            conn.execute(text("ALTER TABLE post ADD COLUMN html_content TEXT"))
            conn.commit()
        logger.info("Added html_content column to post table")
    logger.info("Schema migrations applied")
