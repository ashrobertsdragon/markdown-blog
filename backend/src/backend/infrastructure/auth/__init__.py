"""Authentication infrastructure module."""

from backend.exceptions import AuthenticationError
from backend.infrastructure.auth.clerk_auth_adapter import ClerkAuthAdapter

__all__ = ["AuthenticationError", "ClerkAuthAdapter"]
