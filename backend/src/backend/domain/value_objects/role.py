"""Role value object representing user authorization levels.

This module defines the Role enum which represents the three authorization
levels in the system: AUTHENTICATED, AUTHOR, and ADMIN.
"""

from enum import StrEnum, auto


class Role(StrEnum):
    """User role enum defining authorization levels.

    Roles form a hierarchy where ADMIN > AUTHOR > AUTHENTICATED.
    Each role grants access to specific endpoints based on authorization
    requirements.

    Attributes:
        AUTHENTICATED: Basic authenticated user with read-only access.
        AUTHOR: Content creator with post management capabilities.
        ADMIN: Administrator with full system access.
    """

    AUTHENTICATED = auto()
    AUTHOR = auto()
    ADMIN = auto()

    def can_access_author_endpoints(self) -> bool:
        """Check if this role can access author-only endpoints.

        Returns:
            True if role is AUTHOR or ADMIN, False otherwise.
        """
        return self in (Role.AUTHOR, Role.ADMIN)

    def can_access_admin_endpoints(self) -> bool:
        """Check if this role can access admin-only endpoints.

        Returns:
            True if role is ADMIN, False otherwise.
        """
        return self == Role.ADMIN
