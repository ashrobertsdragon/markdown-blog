"""Database schema creation script for production deployment."""

import sys

from backend.infrastructure.persistence.database import get_engine
from backend.infrastructure.persistence.models import SQLModel


def create_schema() -> int:
    """Create all database tables."""
    try:
        print("Creating database schema...")
        engine = get_engine()
        SQLModel.metadata.create_all(engine)
        print("Schema creation completed successfully")
        return 0
    except Exception as e:
        print(f"ERROR: Schema creation failed: {e}", file=sys.stderr)
        return 1


def main() -> None:
    """Create schema and exit."""
    sys.exit(create_schema())


if __name__ == "__main__":
    main()
