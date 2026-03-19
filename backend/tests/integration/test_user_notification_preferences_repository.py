"""Integration tests for UserNotificationPreferencesRepository."""

from collections.abc import Generator
from datetime import UTC, datetime

import pytest
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, SQLModel, create_engine, select
from sqlmodel.pool import StaticPool

from backend.domain.aggregates.notification_preferences import (
    NotificationPreferences,
)
from backend.infrastructure.persistence import (  # noqa: E501
    user_notification_preferences_repository as _prefs_mod,
)
from backend.infrastructure.persistence.models import (
    User,
    UserNotificationPreferencesModel,
)

UserNotificationPreferencesRepository = (
    _prefs_mod.UserNotificationPreferencesRepository
)


@pytest.fixture(name="session")
def session_fixture() -> Generator[Session]:
    """Create in-memory SQLite database for testing."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    try:
        with Session(engine) as session:
            yield session
    finally:
        engine.dispose()


@pytest.fixture
def test_user(session: Session) -> tuple[User, int]:
    """Create test user in database and return user with guaranteed ID.

    Args:
        session: In-memory SQLite session.
    """
    user = User(email="prefs@example.com", role="authenticated")
    session.add(user)
    session.commit()
    session.refresh(user)
    assert user.id is not None
    return user, user.id


@pytest.fixture
def preferences_repository(
    session: Session,
) -> UserNotificationPreferencesRepository:
    """Return a repository bound to the in-memory session.

    Args:
        session: In-memory SQLite session.
    """
    return UserNotificationPreferencesRepository(session=session)


class TestGetPreferences:
    """Test get_preferences query including auto-creation of defaults."""

    def test_gets_existing_preferences(
        self,
        session: Session,
        test_user: tuple[User, int],
        preferences_repository: UserNotificationPreferencesRepository,
    ) -> None:
        """Test that get_preferences returns previously saved preferences.

        Args:
            session: In-memory SQLite session.
            test_user: Tuple of User and its database ID.
            preferences_repository: Repository under test.
        """
        _, user_id = test_user
        now = datetime.now(UTC)
        model = UserNotificationPreferencesModel(
            user_id=user_id,
            notify_on_comment_replies=False,
            notify_on_mentions=True,
            notify_on_new_posts=False,
            created_at=now,
            updated_at=now,
        )
        session.add(model)
        session.commit()

        prefs = preferences_repository.get_preferences(user_id)

        assert prefs.user_id == user_id
        assert prefs.notify_on_comment_replies is False
        assert prefs.notify_on_mentions is True
        assert prefs.notify_on_new_posts is False

    def test_creates_defaults_if_missing(
        self,
        test_user: tuple[User, int],
        preferences_repository: UserNotificationPreferencesRepository,
    ) -> None:
        """Test that get_preferences creates a default row when none exists.

        Args:
            test_user: Tuple of User and its database ID.
            preferences_repository: Repository under test.
        """
        _, user_id = test_user

        prefs = preferences_repository.get_preferences(user_id)

        assert prefs.user_id == user_id
        assert prefs.notify_on_comment_replies is True
        assert prefs.notify_on_mentions is True
        assert prefs.notify_on_new_posts is True

    def test_never_returns_none(
        self,
        test_user: tuple[User, int],
        preferences_repository: UserNotificationPreferencesRepository,
    ) -> None:
        """Test that get_preferences always returns a NotificationPreferences.

        Args:
            test_user: Tuple of User and its database ID.
            preferences_repository: Repository under test.
        """
        _, user_id = test_user

        prefs = preferences_repository.get_preferences(user_id)

        assert prefs is not None
        assert isinstance(prefs, NotificationPreferences)


class TestUpdatePreferences:
    """Test update_preferences mutation and validation."""

    def test_updates_single_field(
        self,
        test_user: tuple[User, int],
        preferences_repository: UserNotificationPreferencesRepository,
    ) -> None:
        """Test that a single field change is persisted after update.

        Args:
            test_user: Tuple of User and its database ID.
            preferences_repository: Repository under test.
        """
        _, user_id = test_user
        prefs = preferences_repository.get_preferences(user_id)
        prefs.notify_on_comment_replies = False

        preferences_repository.update_preferences(user_id, prefs)
        reloaded = preferences_repository.get_preferences(user_id)

        assert reloaded.notify_on_comment_replies is False

    def test_updates_multiple_fields(
        self,
        test_user: tuple[User, int],
        preferences_repository: UserNotificationPreferencesRepository,
    ) -> None:
        """Test that multiple field changes are all persisted after update.

        Args:
            test_user: Tuple of User and its database ID.
            preferences_repository: Repository under test.
        """
        _, user_id = test_user
        prefs = preferences_repository.get_preferences(user_id)
        prefs.notify_on_comment_replies = False
        prefs.notify_on_new_posts = False

        preferences_repository.update_preferences(user_id, prefs)
        reloaded = preferences_repository.get_preferences(user_id)

        assert reloaded.notify_on_comment_replies is False
        assert reloaded.notify_on_new_posts is False

    def test_preserves_user_id(
        self,
        test_user: tuple[User, int],
        preferences_repository: UserNotificationPreferencesRepository,
    ) -> None:
        """Test that user_id is not altered by update_preferences.

        Args:
            test_user: Tuple of User and its database ID.
            preferences_repository: Repository under test.
        """
        _, user_id = test_user
        prefs = preferences_repository.get_preferences(user_id)
        prefs.notify_on_mentions = False

        preferences_repository.update_preferences(user_id, prefs)
        reloaded = preferences_repository.get_preferences(user_id)

        assert reloaded.user_id == user_id

    def test_raises_valueerror_if_user_missing(
        self,
        preferences_repository: UserNotificationPreferencesRepository,
    ) -> None:
        """Test that update_preferences raises ValueError for unknown user.

        Args:
            preferences_repository: Repository under test.
        """
        prefs = NotificationPreferences.create_defaults(user_id=99999)

        with pytest.raises(ValueError):
            preferences_repository.update_preferences(99999, prefs)


class TestDisableAll:
    """Test disable_all bulk-flag method."""

    def test_disables_all_flags(
        self,
        test_user: tuple[User, int],
        preferences_repository: UserNotificationPreferencesRepository,
    ) -> None:
        """Test that disable_all sets every boolean flag to False.

        Args:
            test_user: Tuple of User and its database ID.
            preferences_repository: Repository under test.
        """
        _, user_id = test_user
        preferences_repository.get_preferences(user_id)

        preferences_repository.disable_all(user_id)
        reloaded = preferences_repository.get_preferences(user_id)

        assert reloaded.notify_on_comment_replies is False
        assert reloaded.notify_on_mentions is False
        assert reloaded.notify_on_new_posts is False

    def test_updates_updated_at(
        self,
        session: Session,
        test_user: tuple[User, int],
        preferences_repository: UserNotificationPreferencesRepository,
    ) -> None:
        """Test that disable_all advances the updated_at timestamp.

        Args:
            session: In-memory SQLite session.
            test_user: Tuple of User and its database ID.
            preferences_repository: Repository under test.
        """
        _, user_id = test_user
        before = datetime.now(UTC)
        preferences_repository.get_preferences(user_id)

        preferences_repository.disable_all(user_id)

        row = session.exec(
            select(UserNotificationPreferencesModel).where(
                UserNotificationPreferencesModel.user_id == user_id
            )
        ).first()
        assert row is not None
        updated_at = row.updated_at
        if updated_at.tzinfo is None:
            updated_at = updated_at.replace(tzinfo=UTC)
        assert updated_at >= before


class TestExists:
    """Test exists check method."""

    def test_returns_true_if_exists(
        self,
        test_user: tuple[User, int],
        preferences_repository: UserNotificationPreferencesRepository,
    ) -> None:
        """Test exists returns True after get_preferences creates defaults.

        Args:
            test_user: Tuple of User and its database ID.
            preferences_repository: Repository under test.
        """
        _, user_id = test_user
        preferences_repository.get_preferences(user_id)

        assert preferences_repository.exists(user_id) is True

    def test_returns_false_if_missing(
        self,
        preferences_repository: UserNotificationPreferencesRepository,
    ) -> None:
        """Test exists returns False for a user_id with no stored preferences.

        Args:
            preferences_repository: Repository under test.
        """
        assert preferences_repository.exists(99999) is False


class TestDefaults:
    """Test default values on NotificationPreferences aggregate."""

    def test_all_notifications_enabled_by_default(self) -> None:
        """Test create_defaults produces all-True preference flags."""
        prefs = NotificationPreferences.create_defaults(user_id=1)

        assert prefs.notify_on_comment_replies is True
        assert prefs.notify_on_mentions is True
        assert prefs.notify_on_new_posts is True

    def test_created_at_set(
        self,
        test_user: tuple[User, int],
        preferences_repository: UserNotificationPreferencesRepository,
        session: Session,
    ) -> None:
        """Test that get_preferences sets created_at on the persisted row.

        Args:
            test_user: Tuple of User and its database ID.
            preferences_repository: Repository under test.
            session: In-memory SQLite session.
        """
        _, user_id = test_user

        preferences_repository.get_preferences(user_id)

        row = session.exec(
            select(UserNotificationPreferencesModel).where(
                UserNotificationPreferencesModel.user_id == user_id
            )
        ).first()
        assert row is not None
        assert row.created_at is not None


class TestConstraints:
    """Test database-level constraints on UserNotificationPreferencesModel."""

    def test_unique_constraint_user_id(
        self,
        session: Session,
        test_user: tuple[User, int],
    ) -> None:
        """Test that inserting two rows with same user_id raises IntegrityError.

        Args:
            session: In-memory SQLite session.
            test_user: Tuple of User and its database ID.
        """

        _, user_id = test_user
        now = datetime.now(UTC)
        first = UserNotificationPreferencesModel(
            user_id=user_id,
            created_at=now,
            updated_at=now,
        )
        session.add(first)
        session.commit()

        duplicate = UserNotificationPreferencesModel(
            user_id=user_id,
            created_at=now,
            updated_at=now,
        )
        session.add(duplicate)
        with pytest.raises(IntegrityError):
            session.commit()

    def test_foreign_key_user_id_enforced(
        self,
        session: Session,
    ) -> None:
        """Test that an invalid user_id FK raises IntegrityError.

        Args:
            session: In-memory SQLite session.
        """
        from sqlalchemy import text

        session.connection().execute(text("PRAGMA foreign_keys=ON"))
        now = datetime.now(UTC)
        row = UserNotificationPreferencesModel(
            user_id=99999,
            created_at=now,
            updated_at=now,
        )
        session.add(row)

        with pytest.raises(IntegrityError):
            session.commit()
