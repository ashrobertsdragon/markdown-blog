"""UserRepository implementation for persistence layer.

This module provides the repository pattern implementation for User aggregates,
bridging between the domain layer and the database infrastructure layer.
Handles conversion between SQLModel User table and domain User aggregate.
"""

from datetime import UTC

from sqlmodel import Session, col, select

from backend.domain.aggregates.user import User as DomainUser
from backend.domain.value_objects.role import Role
from backend.infrastructure.persistence.database import get_db
from backend.infrastructure.persistence.models import User as UserModel


class UserRepository:
    """Repository for User aggregate persistence operations.

    Implements the repository pattern to provide clean separation between
    domain logic and database infrastructure. Handles all CRUD operations
    and conversions between database models and domain aggregates.

    Attributes:
        session: Optional SQLModel Session for dependency injection.
                 If None, uses get_db() context manager.
    """

    def __init__(self, session: Session | None = None) -> None:
        """Initialize repository with optional session injection.

        Args:
            session: Optional SQLModel Session for testing or transactions.
                     If None, repository creates sessions via get_db().
        """
        self._session = session

    def find_by_clerk_id(self, clerk_user_id: str) -> DomainUser | None:
        """Find user by Clerk user ID.

        Uses indexed query on clerk_user_id column for fast lookup.
        Converts database model to domain aggregate if found.

        Args:
            clerk_user_id: Clerk's unique user identifier

        Returns:
            DomainUser aggregate if found, None otherwise
        """
        statement = select(UserModel).where(
            UserModel.clerk_user_id == clerk_user_id
        )

        if self._session:
            user_model = self._session.exec(statement).first()
            if user_model:
                return self._to_domain(user_model)
            return None

        for session in get_db():
            user_model = session.exec(statement).first()
            if user_model:
                return self._to_domain(user_model)
            return None

        return None

    def find_by_id(self, user_id: int) -> DomainUser | None:
        """Find user by primary key ID.

        Uses efficient primary key lookup via session.get().
        Converts database model to domain aggregate if found.

        Args:
            user_id: Database primary key

        Returns:
            DomainUser aggregate if found, None otherwise
        """
        if self._session:
            user_model = self._session.get(UserModel, user_id)
            if user_model:
                return self._to_domain(user_model)
            return None

        for session in get_db():
            user_model = session.get(UserModel, user_id)
            if user_model:
                return self._to_domain(user_model)
            return None

        return None

    def save(self, user: DomainUser) -> DomainUser:
        """Save or update user in database.

        Handles both INSERT (when user.id is None) and UPDATE (when
        user.id exists). For inserts, assigns database-generated ID to
        returned aggregate. For updates, preserves created_at timestamp
        for audit trail integrity.

        Args:
            user: DomainUser aggregate to persist

        Returns:
            DomainUser aggregate with updated ID and database state

        Raises:
            ValueError: If attempting to update non-existent user
            IntegrityError: If duplicate clerk_user_id constraint violated
        """
        if self._session:
            return self._save_with_session(self._session, user)

        for session in get_db():
            return self._save_with_session(session, user)

        raise RuntimeError("Failed to obtain database session")

    def list_all(self, limit: int = 50, offset: int = 0) -> list[DomainUser]:
        """List all users with pagination.

        Returns users ordered by created_at DESC (newest first).
        Applies LIMIT and OFFSET for pagination support.

        Args:
            limit: Maximum number of users to return (default: 50)
            offset: Number of users to skip (default: 0)

        Returns:
            List of DomainUser aggregates, empty list if no users found
        """
        statement = (
            select(UserModel)
            .order_by(col(UserModel.created_at).desc())
            .limit(limit)
            .offset(offset)
        )

        if self._session:
            user_models = self._session.exec(statement).all()
            return [self._to_domain(model) for model in user_models]

        for session in get_db():
            user_models = session.exec(statement).all()
            return [self._to_domain(model) for model in user_models]

        raise RuntimeError("Failed to obtain database session")

    def _save_with_session(
        self, session: Session, user: DomainUser
    ) -> DomainUser:
        """Internal save method with session handling.

        Args:
            session: SQLModel Session to use
            user: DomainUser aggregate to persist

        Returns:
            DomainUser aggregate with updated database state

        Raises:
            ValueError: If attempting to update non-existent user
        """
        if user.id is None:
            user_model = self._to_model(user)
            session.add(user_model)
            session.commit()
            session.refresh(user_model)
            return self._to_domain(user_model)

        existing_model = session.get(UserModel, user.id)
        if not existing_model:
            raise ValueError(f"User with id {user.id} not found")

        existing_model.email = user.email
        existing_model.role = user.role.value
        existing_model.clerk_user_id = user.clerk_user_id
        existing_model.created_at = user.created_at

        session.commit()
        session.refresh(existing_model)
        return self._to_domain(existing_model)

    def _to_domain(self, user_model: UserModel) -> DomainUser:
        """Convert UserModel to DomainUser aggregate.

        Performs infrastructure-to-domain conversion with role string-to-enum
        transformation. Preserves all timestamps for audit trail integrity.
        Ensures timezone-aware datetimes by adding UTC timezone if missing.

        Args:
            user_model: SQLModel User table instance

        Returns:
            DomainUser aggregate with converted Role enum
        """
        created_at = user_model.created_at
        if created_at.tzinfo is None:
            created_at = created_at.replace(tzinfo=UTC)

        return DomainUser(
            id=user_model.id,
            clerk_user_id=user_model.clerk_user_id or "",
            email=user_model.email,
            role=Role(user_model.role),
            created_at=created_at,
        )

    def _to_model(self, domain_user: DomainUser) -> UserModel:
        """Convert DomainUser aggregate to UserModel.

        Performs domain-to-infrastructure conversion with role enum-to-string
        transformation. Preserves all timestamps for database storage.

        Args:
            domain_user: Domain User aggregate

        Returns:
            SQLModel User table instance ready for persistence
        """
        return UserModel(
            id=domain_user.id,
            clerk_user_id=domain_user.clerk_user_id,
            email=domain_user.email,
            role=domain_user.role.value,
            created_at=domain_user.created_at,
        )
