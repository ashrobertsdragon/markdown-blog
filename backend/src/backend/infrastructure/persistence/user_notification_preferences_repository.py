"""UserNotificationPreferencesRepository for the notification bounded context.

Provides the repository pattern implementation for NotificationPreferences
aggregates, bridging between the domain layer and the database infrastructure
layer. Handles conversion between UserNotificationPreferencesModel and
NotificationPreferences domain aggregate.
"""

from datetime import UTC, datetime

from sqlmodel import Session, select

from backend.domain.aggregates.notification_preferences import (
    NotificationPreferences,
)
from backend.infrastructure.persistence.database import get_db
from backend.infrastructure.persistence.models import (
    UserNotificationPreferencesModel,
)


class UserNotificationPreferencesRepository:
    """Repository for NotificationPreferences aggregate persistence.

    Implements the repository pattern to provide clean separation between
    domain logic and database infrastructure. Auto-creates default preferences
    on first read if none exist (opt-out model).

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

    def get_preferences(self, user_id: int) -> NotificationPreferences:
        """Return preferences for user, creating defaults if none exist.

        Args:
            user_id: Primary key of the User whose preferences to fetch.

        Returns:
            NotificationPreferences aggregate, never None.
        """
        if self._session:
            return self._get_or_create_with_session(self._session, user_id)

        for session in get_db():
            return self._get_or_create_with_session(session, user_id)

        raise RuntimeError("Failed to obtain database session")

    def update_preferences(
        self, user_id: int, preferences: NotificationPreferences
    ) -> None:
        """Persist updated preference flags for an existing user row.

        Args:
            user_id: Primary key of the User whose preferences to update.
            preferences: NotificationPreferences aggregate with new values.

        Raises:
            ValueError: If no preferences row exists for user_id, or if
                preferences.user_id does not match user_id.
        """
        if self._session:
            self._update_with_session(self._session, user_id, preferences)
            return

        for session in get_db():
            self._update_with_session(session, user_id, preferences)
            return

        raise RuntimeError("Failed to obtain database session")

    def disable_all(self, user_id: int) -> None:
        """Set all three notification flags to False for a user.

        Creates a default row with all flags False if none exists yet.

        Args:
            user_id: Primary key of the User to disable notifications for.
        """
        if self._session:
            self._disable_all_with_session(self._session, user_id)
            return

        for session in get_db():
            self._disable_all_with_session(session, user_id)
            return

        raise RuntimeError("Failed to obtain database session")

    def exists(self, user_id: int) -> bool:
        """Return True if a preferences row exists for user_id.

        Args:
            user_id: Primary key of the User to check.

        Returns:
            True if a row is present, False otherwise.
        """
        statement = select(UserNotificationPreferencesModel).where(
            UserNotificationPreferencesModel.user_id == user_id
        )

        if self._session:
            return self._session.exec(statement).first() is not None

        for session in get_db():
            return session.exec(statement).first() is not None

        return False

    def _get_or_create_with_session(
        self, session: Session, user_id: int
    ) -> NotificationPreferences:
        """Fetch or insert default preferences with explicit session.

        Args:
            session: SQLModel Session to use.
            user_id: Primary key of the User.

        Returns:
            NotificationPreferences aggregate.
        """
        statement = select(UserNotificationPreferencesModel).where(
            UserNotificationPreferencesModel.user_id == user_id
        )
        model = session.exec(statement).first()

        if model is None:
            defaults = NotificationPreferences.create_defaults(user_id)
            model = self._to_model(defaults)
            session.add(model)
            session.commit()
            session.refresh(model)

        return self._to_domain(model)

    def _update_with_session(
        self,
        session: Session,
        user_id: int,
        preferences: NotificationPreferences,
    ) -> None:
        """Internal update method with explicit session.

        Args:
            session: SQLModel Session to use.
            user_id: Primary key of the User.
            preferences: NotificationPreferences with updated values.

        Raises:
            ValueError: If no row exists for user_id, or if
                preferences.user_id does not match user_id.
        """
        if preferences.user_id != user_id:
            raise ValueError(
                "preferences.user_id does not match the requested user_id"
            )

        statement = select(UserNotificationPreferencesModel).where(
            UserNotificationPreferencesModel.user_id == user_id
        )
        model = session.exec(statement).first()

        if model is None:
            raise ValueError("No preferences found for the specified user")

        model.notify_on_comment_replies = preferences.notify_on_comment_replies
        model.notify_on_mentions = preferences.notify_on_mentions
        model.notify_on_new_posts = preferences.notify_on_new_posts
        model.updated_at = datetime.now(UTC)
        session.commit()

    def _disable_all_with_session(self, session: Session, user_id: int) -> None:
        """Internal disable-all method with explicit session.

        Args:
            session: SQLModel Session to use.
            user_id: Primary key of the User.
        """
        statement = select(UserNotificationPreferencesModel).where(
            UserNotificationPreferencesModel.user_id == user_id
        )
        model = session.exec(statement).first()

        if model is None:
            model = UserNotificationPreferencesModel(
                user_id=user_id,
                notify_on_comment_replies=False,
                notify_on_mentions=False,
                notify_on_new_posts=False,
            )
            session.add(model)
            session.commit()
            return

        model.notify_on_comment_replies = False
        model.notify_on_mentions = False
        model.notify_on_new_posts = False
        model.updated_at = datetime.now(UTC)
        session.commit()

    def _to_domain(
        self, model: UserNotificationPreferencesModel
    ) -> NotificationPreferences:
        """Convert UserNotificationPreferencesModel to domain aggregate.

        Args:
            model: UserNotificationPreferencesModel database table instance.

        Returns:
            NotificationPreferences aggregate with all fields populated.
        """
        return NotificationPreferences(
            user_id=model.user_id,
            notify_on_comment_replies=model.notify_on_comment_replies,
            notify_on_mentions=model.notify_on_mentions,
            notify_on_new_posts=model.notify_on_new_posts,
        )

    def _to_model(
        self, preferences: NotificationPreferences
    ) -> UserNotificationPreferencesModel:
        """Convert NotificationPreferences domain aggregate to model.

        Args:
            preferences: NotificationPreferences domain aggregate to convert.

        Returns:
            UserNotificationPreferencesModel instance ready for persistence.
        """
        return UserNotificationPreferencesModel(
            user_id=preferences.user_id,
            notify_on_comment_replies=preferences.notify_on_comment_replies,
            notify_on_mentions=preferences.notify_on_mentions,
            notify_on_new_posts=preferences.notify_on_new_posts,
        )
