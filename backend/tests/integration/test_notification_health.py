"""Integration tests for notification health metrics with a real database.

Uses an in-memory SQLite database to verify that NotificationMetrics
calculations are correct against actual persisted Notification records.
No mocks are used — these tests exercise the full repository + metrics path.
"""

from collections.abc import Generator
from datetime import UTC, datetime, timedelta

import pytest
from backend.infrastructure.monitoring.notification_metrics import (
    NotificationMetrics,
)
from sqlmodel import Session, SQLModel, create_engine

from backend.domain.aggregates.notification import (
    EventType,
    NotificationStatus,
)
from backend.infrastructure.persistence.models import (
    CommentModel,
    NotificationModel,
    Post,
    User,
)
from backend.infrastructure.persistence.notification_repository import (
    NotificationRepository,
)


@pytest.fixture(name="session")
def session_fixture() -> Generator[Session]:
    """Provide an in-memory SQLite session with all tables created."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
    )
    SQLModel.metadata.create_all(engine)
    try:
        with Session(engine) as session:
            yield session
    finally:
        engine.dispose()


@pytest.fixture
def repo(session: Session) -> NotificationRepository:
    """Return a NotificationRepository bound to the in-memory session."""
    return NotificationRepository(session=session)


@pytest.fixture
def metrics(repo: NotificationRepository) -> NotificationMetrics:
    """Return a NotificationMetrics instance backed by the test repository."""
    return NotificationMetrics(repo)


def _seed_users(session: Session) -> tuple[int, int]:
    """Insert a recipient and sender user, return their IDs."""
    recipient = User(email="recipient@example.com", role="authenticated")
    sender = User(email="sender@example.com", role="authenticated")
    session.add(recipient)
    session.add(sender)
    session.commit()
    session.refresh(recipient)
    session.refresh(sender)
    assert recipient.id is not None
    assert sender.id is not None
    return recipient.id, sender.id


def _seed_post(session: Session, author_id: int) -> int:
    """Insert a post and return its ID."""
    post = Post(
        slug="test-post",
        title="Test Post",
        html_content="<p>content</p>",
        published=False,
        author_id=author_id,
    )
    session.add(post)
    session.commit()
    session.refresh(post)
    assert post.id is not None
    return post.id


def _seed_comment(session: Session, post_id: int, author_id: int) -> int:
    """Insert a comment and return its ID."""
    now = datetime.now(UTC)
    comment = CommentModel(
        post_id=post_id,
        author_id=author_id,
        text="Test comment",
        created_at=now,
        updated_at=now,
    )
    session.add(comment)
    session.commit()
    session.refresh(comment)
    assert comment.id is not None
    return comment.id


def _insert_notification(
    session: Session,
    *,
    recipient_id: int,
    sender_id: int,
    post_id: int,
    comment_id: int,
    status: NotificationStatus,
    created_at: datetime,
) -> None:
    """Insert a NotificationModel row directly with a controlled created_at."""
    model = NotificationModel(
        recipient_id=recipient_id,
        sender_id=sender_id,
        event_type=str(EventType.COMMENT_POSTED),
        post_id=post_id,
        comment_id=comment_id,
        status=str(status),
        attempt_count=0,
        created_at=created_at,
        sent_at=None,
        error_message=None,
        next_retry_at=None,
    )
    session.add(model)
    session.commit()


class TestHealthCheckWithDatabase:
    """NotificationMetrics reflects the real state of the database."""

    def test_sent_count_matches_database(
        self, session: Session, metrics: NotificationMetrics
    ) -> None:
        """Sent count in health summary equals the number of SENT rows."""
        recipient_id, sender_id = _seed_users(session)
        post_id = _seed_post(session, recipient_id)
        comment_id = _seed_comment(session, post_id, recipient_id)
        now = datetime.now(UTC)

        for _ in range(3):
            _insert_notification(
                session,
                recipient_id=recipient_id,
                sender_id=sender_id,
                post_id=post_id,
                comment_id=comment_id,
                status=NotificationStatus.SENT,
                created_at=now,
            )

        summary = metrics.get_health_summary()
        assert summary["sent"] == 3

    def test_failed_count_matches_database(
        self, session: Session, metrics: NotificationMetrics
    ) -> None:
        """Failed count in health summary equals the number of FAILED rows."""
        recipient_id, sender_id = _seed_users(session)
        post_id = _seed_post(session, recipient_id)
        comment_id = _seed_comment(session, post_id, recipient_id)
        now = datetime.now(UTC)

        for _ in range(2):
            _insert_notification(
                session,
                recipient_id=recipient_id,
                sender_id=sender_id,
                post_id=post_id,
                comment_id=comment_id,
                status=NotificationStatus.FAILED,
                created_at=now,
            )

        summary = metrics.get_health_summary()
        assert summary["failed"] == 2

    def test_stuck_detection_uses_created_at(
        self, session: Session, metrics: NotificationMetrics
    ) -> None:
        """Stuck notifications are identified by created_at age, not status."""
        recipient_id, sender_id = _seed_users(session)
        post_id = _seed_post(session, recipient_id)
        comment_id = _seed_comment(session, post_id, recipient_id)

        old = datetime.now(UTC) - timedelta(hours=2)
        _insert_notification(
            session,
            recipient_id=recipient_id,
            sender_id=sender_id,
            post_id=post_id,
            comment_id=comment_id,
            status=NotificationStatus.PENDING,
            created_at=old,
        )

        summary = metrics.get_health_summary()
        assert summary["stuck_count"] == 1

    def test_failure_rate_matches_database_counts(
        self, session: Session, metrics: NotificationMetrics
    ) -> None:
        """Failure rate is computed from actual sent and failed row counts."""
        recipient_id, sender_id = _seed_users(session)
        post_id = _seed_post(session, recipient_id)
        comment_id = _seed_comment(session, post_id, recipient_id)
        now = datetime.now(UTC)

        for _ in range(8):
            _insert_notification(
                session,
                recipient_id=recipient_id,
                sender_id=sender_id,
                post_id=post_id,
                comment_id=comment_id,
                status=NotificationStatus.SENT,
                created_at=now,
            )
        for _ in range(2):
            _insert_notification(
                session,
                recipient_id=recipient_id,
                sender_id=sender_id,
                post_id=post_id,
                comment_id=comment_id,
                status=NotificationStatus.FAILED,
                created_at=now,
            )

        summary = metrics.get_health_summary()
        assert summary["failure_rate"] == pytest.approx(20.0)

    def test_end_to_end_health_check_returns_full_summary(
        self, session: Session, metrics: NotificationMetrics
    ) -> None:
        """End-to-end: seeded data produces a complete health summary dict."""
        recipient_id, sender_id = _seed_users(session)
        post_id = _seed_post(session, recipient_id)
        comment_id = _seed_comment(session, post_id, recipient_id)
        now = datetime.now(UTC)

        _insert_notification(
            session,
            recipient_id=recipient_id,
            sender_id=sender_id,
            post_id=post_id,
            comment_id=comment_id,
            status=NotificationStatus.SENT,
            created_at=now,
        )

        summary = metrics.get_health_summary()
        assert set(summary.keys()) == {
            "sent",
            "failed",
            "pending",
            "failure_rate",
            "stuck_count",
            "timestamp",
        }


class TestEdgeCases:
    """Metrics handle boundary conditions without errors."""

    def test_empty_table_returns_zero_counts(
        self, metrics: NotificationMetrics
    ) -> None:
        """All counts and rates are zero when the notifications table is empty."""
        summary = metrics.get_health_summary()
        assert summary["sent"] == 0
        assert summary["failed"] == 0
        assert summary["pending"] == 0
        assert summary["failure_rate"] == 0.0
        assert summary["stuck_count"] == 0

    def test_all_pending_produces_zero_failure_rate(
        self, session: Session, metrics: NotificationMetrics
    ) -> None:
        """Failure rate is 0.0 when every notification is still PENDING."""
        recipient_id, sender_id = _seed_users(session)
        post_id = _seed_post(session, recipient_id)
        comment_id = _seed_comment(session, post_id, recipient_id)
        now = datetime.now(UTC)

        for _ in range(5):
            _insert_notification(
                session,
                recipient_id=recipient_id,
                sender_id=sender_id,
                post_id=post_id,
                comment_id=comment_id,
                status=NotificationStatus.PENDING,
                created_at=now,
            )

        summary = metrics.get_health_summary()
        assert summary["failure_rate"] == 0.0

    def test_all_failed_produces_100_percent_failure_rate(
        self, session: Session, metrics: NotificationMetrics
    ) -> None:
        """Failure rate is 100.0 when all terminal notifications are FAILED."""
        recipient_id, sender_id = _seed_users(session)
        post_id = _seed_post(session, recipient_id)
        comment_id = _seed_comment(session, post_id, recipient_id)
        now = datetime.now(UTC)

        for _ in range(4):
            _insert_notification(
                session,
                recipient_id=recipient_id,
                sender_id=sender_id,
                post_id=post_id,
                comment_id=comment_id,
                status=NotificationStatus.FAILED,
                created_at=now,
            )

        summary = metrics.get_health_summary()
        assert summary["failure_rate"] == 100.0

    def test_mixed_statuses_counts_are_independent(
        self, session: Session, metrics: NotificationMetrics
    ) -> None:
        """Sent, failed, and pending counts are independent of each other."""
        recipient_id, sender_id = _seed_users(session)
        post_id = _seed_post(session, recipient_id)
        comment_id = _seed_comment(session, post_id, recipient_id)
        now = datetime.now(UTC)

        _insert_notification(
            session,
            recipient_id=recipient_id,
            sender_id=sender_id,
            post_id=post_id,
            comment_id=comment_id,
            status=NotificationStatus.SENT,
            created_at=now,
        )
        _insert_notification(
            session,
            recipient_id=recipient_id,
            sender_id=sender_id,
            post_id=post_id,
            comment_id=comment_id,
            status=NotificationStatus.FAILED,
            created_at=now,
        )
        _insert_notification(
            session,
            recipient_id=recipient_id,
            sender_id=sender_id,
            post_id=post_id,
            comment_id=comment_id,
            status=NotificationStatus.PENDING,
            created_at=now,
        )

        summary = metrics.get_health_summary()
        assert summary["sent"] == 1
        assert summary["failed"] == 1
        assert summary["pending"] == 1
