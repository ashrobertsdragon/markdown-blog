"""NotificationRepository implementation for the notification bounded context.

Provides the repository pattern implementation for Notification aggregates,
bridging between the domain layer and the database infrastructure layer.
Handles conversion between NotificationModel (SQLModel table) and Notification
(domain aggregate).
"""

from datetime import UTC, datetime

from sqlalchemy import func, or_
from sqlmodel import Session, col, select

from backend.domain.aggregates.notification import (
    EventType,
    Notification,
    NotificationStatus,
)
from backend.infrastructure.persistence.database import get_db
from backend.infrastructure.persistence.models import NotificationModel


class NotificationRepository:
    """Repository for Notification aggregate persistence operations.

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

    def save(self, notification: Notification) -> Notification:
        """Save or update notification in database.

        Handles both INSERT (when notification.id is None) and UPDATE (when
        notification.id exists). For updates, only mutable fields are written:
        status, attempt_count, sent_at, error_message, next_retry_at.
        Immutable fields (recipient_id, sender_id, event_type, post_id,
        comment_id, created_at) are never overwritten.

        Args:
            notification: Notification aggregate to persist.

        Returns:
            Notification aggregate with database-assigned id on insert,
            or refreshed state on update.

        Raises:
            ValueError: If attempting to update a notification that does not
                exist in the database.
        """
        if self._session:
            return self._save_with_session(self._session, notification)

        for session in get_db():
            return self._save_with_session(session, notification)

        raise RuntimeError("Failed to obtain database session")

    def get_by_id(self, notification_id: int) -> Notification | None:
        """Find notification by primary key.

        Args:
            notification_id: Database primary key of the notification.

        Returns:
            Notification aggregate if found, None otherwise.
        """
        if self._session:
            model = self._session.get(NotificationModel, notification_id)
            return self._to_domain(model) if model else None

        for session in get_db():
            model = session.get(NotificationModel, notification_id)
            return self._to_domain(model) if model else None

        return None

    def get_pending(self, limit: int = 100) -> list[Notification]:
        """Return pending notifications that are due for delivery.

        Filters to status=PENDING and next_retry_at IS NULL or in the past.
        Results are ordered newest-first to surface recent events first.

        Args:
            limit: Maximum number of notifications to return (default: 100,
                   capped at 500 to prevent unbounded memory allocation).

        Returns:
            List of Notification aggregates ready for delivery.
        """
        limit = min(limit, 500)
        now = datetime.now(UTC)
        statement = (
            select(NotificationModel)
            .where(
                NotificationModel.status == NotificationStatus.PENDING,
                or_(
                    col(NotificationModel.next_retry_at).is_(None),
                    col(NotificationModel.next_retry_at) <= now,
                ),
            )
            .order_by(col(NotificationModel.created_at).desc())
            .limit(limit)
        )

        if self._session:
            models = self._session.exec(statement).all()
            return [self._to_domain(m) for m in models]

        for session in get_db():
            models = session.exec(statement).all()
            return [self._to_domain(m) for m in models]

        raise RuntimeError("Failed to obtain database session")

    def get_history(
        self, user_id: int, skip: int = 0, limit: int = 50
    ) -> list[Notification]:
        """Return notification history for a specific recipient.

        Args:
            user_id: Primary key of the recipient User.
            skip: Number of notifications to skip for pagination (default: 0,
                  must be >= 0).
            limit: Maximum number of notifications to return (default: 50,
                   capped at 200).

        Returns:
            List of Notification aggregates ordered newest-first.

        Raises:
            ValueError: If skip is negative.
        """
        if skip < 0:
            raise ValueError("skip must be >= 0")
        limit = min(max(limit, 1), 200)
        statement = (
            select(NotificationModel)
            .where(NotificationModel.recipient_id == user_id)
            .order_by(col(NotificationModel.created_at).desc())
            .offset(skip)
            .limit(limit)
        )

        if self._session:
            models = self._session.exec(statement).all()
            return [self._to_domain(m) for m in models]

        for session in get_db():
            models = session.exec(statement).all()
            return [self._to_domain(m) for m in models]

        raise RuntimeError("Failed to obtain database session")

    def list_for_user(
        self, user_id: int, skip: int = 0, limit: int = 50
    ) -> list[Notification]:
        """Alias for get_history; returns notification history for a recipient.

        Args:
            user_id: Primary key of the recipient User.
            skip: Number of notifications to skip for pagination.
            limit: Maximum number of notifications to return.

        Returns:
            List of Notification aggregates ordered newest-first.
        """
        return self.get_history(user_id, skip=skip, limit=limit)

    def mark_for_retry(
        self, notification_id: int, next_retry_at: datetime
    ) -> None:
        """Schedule a notification for retry at a future time.

        Enforces UTC timezone on next_retry_at to ensure consistent
        comparison with stored timestamps regardless of caller context.

        Args:
            notification_id: Primary key of the notification to reschedule.
            next_retry_at: UTC datetime after which the notification is
                eligible for re-processing. Naive datetimes are assumed UTC.

        Raises:
            ValueError: If notification_id does not exist in the database.
        """
        if next_retry_at.tzinfo is None:
            next_retry_at = next_retry_at.replace(tzinfo=UTC)
        if self._session:
            self._mark_for_retry_with_session(
                self._session, notification_id, next_retry_at
            )
            return

        for session in get_db():
            self._mark_for_retry_with_session(
                session, notification_id, next_retry_at
            )
            return

        raise RuntimeError("Failed to obtain database session")

    def list_all_admin(
        self, skip: int = 0, limit: int = 50
    ) -> list[Notification]:
        """Return all notifications ordered newest-first for admin views.

        Args:
            skip: Number of records to skip (default 0, must be >= 0).
            limit: Maximum records to return (default 50, capped at 200).

        Returns:
            List of Notification aggregates ordered newest-first.

        Raises:
            ValueError: If skip is negative.
        """
        if skip < 0:
            raise ValueError("skip must be >= 0")
        limit = min(max(limit, 1), 200)
        statement = (
            select(NotificationModel)
            .order_by(col(NotificationModel.created_at).desc())
            .offset(skip)
            .limit(limit)
        )

        if self._session:
            models = self._session.exec(statement).all()
            return [self._to_domain(m) for m in models]

        for session in get_db():
            models = session.exec(statement).all()
            return [self._to_domain(m) for m in models]

        raise RuntimeError("Failed to obtain database session")

    def count_all(self) -> int:
        """Return the total count of all notifications.

        Returns:
            Integer count of all notification rows.
        """
        statement = select(func.count()).select_from(NotificationModel)

        if self._session:
            return self._session.exec(statement).one()

        for session in get_db():
            return session.exec(statement).one()

        raise RuntimeError("Failed to obtain database session")

    def count_sent(self) -> int:
        """Return the total count of SENT notifications.

        Returns:
            Integer count of rows with status=SENT.
        """
        statement = select(func.count()).where(
            NotificationModel.status == NotificationStatus.SENT
        )

        if self._session:
            return self._session.exec(statement).one()

        for session in get_db():
            return session.exec(statement).one()

        raise RuntimeError("Failed to obtain database session")

    def count_pending(self) -> int:
        """Return the total count of PENDING notifications.

        Returns:
            Integer count of rows with status=PENDING.
        """
        statement = select(func.count()).where(
            NotificationModel.status == NotificationStatus.PENDING
        )

        if self._session:
            return self._session.exec(statement).one()

        for session in get_db():
            return session.exec(statement).one()

        raise RuntimeError("Failed to obtain database session")

    def count_failed(self) -> int:
        """Return the total count of FAILED notifications.

        Returns:
            Integer count of rows with status=FAILED.
        """
        statement = select(func.count()).where(
            NotificationModel.status == NotificationStatus.FAILED
        )

        if self._session:
            return self._session.exec(statement).one()

        for session in get_db():
            return session.exec(statement).one()

        raise RuntimeError("Failed to obtain database session")

    def _save_with_session(
        self, session: Session, notification: Notification
    ) -> Notification:
        """Internal save method with explicit session.

        Args:
            session: SQLModel Session to use.
            notification: Notification aggregate to persist.

        Returns:
            Notification aggregate with updated database state.

        Raises:
            ValueError: If attempting to update a non-existent notification.
        """
        if notification.id is None:
            model = self._to_model(notification)
            session.add(model)
            session.commit()
            session.refresh(model)
            return self._to_domain(model)

        existing = session.get(NotificationModel, notification.id)
        if not existing:
            raise ValueError(
                f"Notification with id {notification.id} not found"
            )

        existing.status = str(notification.status)
        existing.attempt_count = notification.attempt_count
        existing.sent_at = notification.sent_at
        existing.error_message = notification.error_message
        existing.next_retry_at = notification.next_retry_at
        existing.resend_email_id = notification.resend_email_id

        session.commit()
        session.refresh(existing)
        return self._to_domain(existing)

    def _mark_for_retry_with_session(
        self,
        session: Session,
        notification_id: int,
        next_retry_at: datetime,
    ) -> None:
        """Internal mark-for-retry method with explicit session.

        Args:
            session: SQLModel Session to use.
            notification_id: Primary key of the notification to update.
            next_retry_at: UTC datetime to set as the next retry time.
        """
        model = session.get(NotificationModel, notification_id)
        if model is None:
            raise ValueError(
                f"Notification with id {notification_id} not found"
            )
        model.next_retry_at = next_retry_at
        session.commit()

    def _to_domain(self, model: NotificationModel) -> Notification:
        """Convert NotificationModel to Notification domain aggregate.

        Ensures all datetimes are timezone-aware by attaching UTC when the
        driver returns naive datetimes (e.g. MySQL, some SQLite configs).

        Args:
            model: NotificationModel database table instance.

        Returns:
            Notification aggregate with all fields populated and UTC datetimes.
        """
        created_at = model.created_at
        if created_at.tzinfo is None:
            created_at = created_at.replace(tzinfo=UTC)

        sent_at = model.sent_at
        if sent_at is not None and sent_at.tzinfo is None:
            sent_at = sent_at.replace(tzinfo=UTC)

        next_retry_at = model.next_retry_at
        if next_retry_at is not None and next_retry_at.tzinfo is None:
            next_retry_at = next_retry_at.replace(tzinfo=UTC)

        return Notification(
            id=model.id,
            recipient_id=model.recipient_id,
            sender_id=model.sender_id,
            event_type=EventType(model.event_type),
            post_id=model.post_id,
            comment_id=model.comment_id,
            status=NotificationStatus(model.status),
            attempt_count=model.attempt_count,
            created_at=created_at,
            sent_at=sent_at,
            error_message=model.error_message,
            next_retry_at=next_retry_at,
            resend_email_id=model.resend_email_id,
        )

    def _to_model(self, notification: Notification) -> NotificationModel:
        """Convert Notification domain aggregate to NotificationModel.

        Args:
            notification: Notification domain aggregate to convert.

        Returns:
            NotificationModel instance ready for persistence.
        """
        return NotificationModel(
            id=notification.id,
            recipient_id=notification.recipient_id,
            sender_id=notification.sender_id,
            event_type=str(notification.event_type),
            post_id=notification.post_id,
            comment_id=notification.comment_id,
            status=str(notification.status),
            attempt_count=notification.attempt_count,
            created_at=notification.created_at,
            sent_at=notification.sent_at,
            error_message=notification.error_message,
            next_retry_at=notification.next_retry_at,
            resend_email_id=notification.resend_email_id,
        )
