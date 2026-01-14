"""User aggregate for authentication bounded context."""

from dataclasses import dataclass
from datetime import UTC, datetime

from backend.domain.value_objects.role import Role


@dataclass(frozen=False)
class User:
    """User aggregate root representing an authenticated user.

    Manages user identity, role assignments, and authentication state.
    Part of the Identity & Access bounded context.
    """

    id: int | None
    clerk_user_id: str | None
    email: str
    role: Role
    created_at: datetime

    def __setattr__(self, name: str, value: object) -> None:
        """Prevent modification of created_at field after initialization."""
        if name == "created_at" and hasattr(self, "created_at"):
            raise AttributeError(
                "Cannot modify created_at timestamp - audit trail integrity"
            )
        object.__setattr__(self, name, value)

    @classmethod
    def create_from_clerk(cls, clerk_user_id: str, email: str) -> "User":
        """Create new user from Clerk authentication.

        Factory method called when a user first authenticates via Clerk.
        Sets initial role to AUTHENTICATED and current timestamp.

        Args:
            clerk_user_id: Clerk's unique user identifier
            email: User's email from Clerk profile

        Returns:
            New User aggregate ready for persistence

        Raises:
            ValueError: If clerk_user_id or email are empty
        """
        if not clerk_user_id:
            raise ValueError("clerk_user_id cannot be empty")
        if not email:
            raise ValueError("email cannot be empty")

        return cls(
            id=None,
            clerk_user_id=clerk_user_id,
            email=email,
            role=Role.AUTHENTICATED,
            created_at=datetime.now(UTC),
        )

    def change_role(self, new_role: Role) -> None:
        """Change user role.

        Updates the user's role to the specified new role.

        Args:
            new_role: The new Role value object to assign

        Raises:
            ValueError: If new_role is not a valid Role enum
        """
        if not isinstance(new_role, Role):
            raise ValueError("new_role must be a valid Role enum")
        self.role = new_role

    def to_dict(self) -> dict:
        """Serialize user to dictionary for API responses.

        Converts the User aggregate to a JSON-serializable dict.
        Role is serialized as string value.

        Returns:
            Dictionary with all user fields, role as string
        """
        return {
            "id": self.id,
            "clerk_user_id": self.clerk_user_id,
            "email": self.email,
            "role": self.role.value,
            "created_at": self.created_at.isoformat(),
        }
