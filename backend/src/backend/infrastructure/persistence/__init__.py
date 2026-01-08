"""Persistence layer initialization.

This module imports all SQLModel table definitions to ensure they are
registered with SQLModel.metadata before create_all() is called in tests.
"""

from backend.infrastructure.persistence.models import Post, User

__all__ = ["User", "Post"]
