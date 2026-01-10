"""Authentication infrastructure module."""

from backend.infrastructure.auth.clerk_auth_adapter import (
    AuthenticationError,
    ClerkAuthAdapter,
)

__all__ = ["AuthenticationError", "ClerkAuthAdapter"]
