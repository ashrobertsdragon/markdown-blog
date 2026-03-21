"""Integration tests for NotificationRepository CRUD and query operations."""

from collections.abc import Generator
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import inspect as sa_inspect
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, SQLModel, create_engine, select, text
from sqlmodel.pool import StaticPool

from backend.domain.aggregates.notification import (
    EventType,
    Notification,
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
    """Create test recipient user in database and return user with ID.

    Args:
        session: In-memory SQLite session.
    """
    user = User(email="recipient@example.com", role="authenticated")
    session.add(user)
    session.commit()
    session.refresh(user)
    assert user.id is not None
    return user, user.id


@pytest.fixture
def test_sender(session: Session) -> tuple[User, int]:
    """Create test sender user in database and return user with guaranteed ID.

    Args:
        session: In-memory SQLite session.
    """
    sender = User(email="sender@example.com", role="authenticated")
    session.add(sender)
    session.commit()
    session.refresh(sender)
    assert sender.id is not None
    return sender, sender.id


@pytest.fixture
def test_post(
    session: Session,
    test_user: tuple[User, int],
    test_sender: tuple[User, int],
) -> tuple[Post, int]:
    """Create test post in database and return post with guaranteed ID.

    Args:
        session: In-memory SQLite session.
        test_user: Tuple of recipient User and its database ID.
        test_sender: Tuple of sender User and its database ID.
    """
    _, author_id = test_user
    post = Post(
        slug="test-post",
        title="Test Post",
        html_content="<p>Test content</p>",
        published=False,
        author_id=author_id,
    )
    session.add(post)
    session.commit()
    session.refresh(post)
    assert post.id is not None
    return post, post.id


@pytest.fixture
def test_comment(
    session: Session,
    test_user: tuple[User, int],
    test_sender: tuple[User, int],
    test_post: tuple[Post, int],
) -> tuple[CommentModel, int]:
    """Create test comment in database and return comment with guaranteed ID.

    Args:
        session: In-memory SQLite session.
        test_user: Tuple of recipient User and its database ID.
        test_sender: Tuple of sender User and its database ID.
        test_post: Tuple of Post and its database ID.
    """
    _, author_id = test_user
    _, post_id = test_post
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
    return comment, comment.id


@pytest.fixture
def notification_repository(session: Session) -> NotificationRepository:
    """Return a NotificationRepository bound to the in-memory session.

    Args:
        session: In-memory SQLite session.
    """
    return NotificationRepository(session=session)


class TestSave:
    """Test save operation for new inserts and updates."""

    def test_saves_new_notification(
        self,
        session: Session,
        test_user: tuple[User, int],
        test_sender: tuple[User, int],
        test_post: tuple[Post, int],
        test_comment: tuple[CommentModel, int],
        notification_repository: NotificationRepository,
    ) -> None:
        """Test that saving a new Notification inserts a row with correct
        fields.

        Args:
            session: In-memory SQLite session.
            test_user: Tuple of recipient User and its database ID.
            test_sender: Tuple of sender User and its database ID.
            test_post: Tuple of Post and its database ID.
            test_comment: Tuple of CommentModel and its database ID.
            notification_repository: Repository under test.
        """
        _, recipient_id = test_user
        _, sender_id = test_sender
        _, post_id = test_post
        _, comment_id = test_comment
        notification = Notification.create(
            recipient_id=recipient_id,
            sender_id=sender_id,
            event_type=EventType.COMMENT_POSTED,
            post_id=post_id,
            comment_id=comment_id,
        )

        saved = notification_repository.save(notification)

        statement = select(NotificationModel).where(
            NotificationModel.id == saved.id
        )
        row = session.exec(statement).first()
        assert row is not None
        assert row.recipient_id == recipient_id
        assert row.sender_id == sender_id
        assert row.event_type == EventType.COMMENT_POSTED
        assert row.post_id == post_id
        assert row.comment_id == comment_id

    def test_save_assigns_id(
        self,
        test_user: tuple[User, int],
        test_sender: tuple[User, int],
        test_post: tuple[Post, int],
        test_comment: tuple[CommentModel, int],
        notification_repository: NotificationRepository,
    ) -> None:
        """Test that save returns a Notification with a database-assigned id.

        Args:
            test_user: Tuple of recipient User and its database ID.
            test_sender: Tuple of sender User and its database ID.
            test_post: Tuple of Post and its database ID.
            test_comment: Tuple of CommentModel and its database ID.
            notification_repository: Repository under test.
        """
        _, recipient_id = test_user
        _, sender_id = test_sender
        _, post_id = test_post
        _, comment_id = test_comment
        notification = Notification.create(
            recipient_id=recipient_id,
            sender_id=sender_id,
            event_type=EventType.COMMENT_POSTED,
            post_id=post_id,
            comment_id=comment_id,
        )
        assert notification.id is None

        saved = notification_repository.save(notification)

        assert saved.id is not None
        assert isinstance(saved.id, int)

    def test_save_update_modifies_mutable_fields(
        self,
        test_user: tuple[User, int],
        test_sender: tuple[User, int],
        test_post: tuple[Post, int],
        test_comment: tuple[CommentModel, int],
        notification_repository: NotificationRepository,
    ) -> None:
        """Test saving a previously saved Notification updates attempt_count,
        status, and next_retry_at.

        Args:
            test_user: Tuple of recipient User and its database ID.
            test_sender: Tuple of sender User and its database ID.
            test_post: Tuple of Post and its database ID.
            test_comment: Tuple of CommentModel and its database ID.
            notification_repository: Repository under test.
        """
        _, recipient_id = test_user
        _, sender_id = test_sender
        _, post_id = test_post
        _, comment_id = test_comment
        notification = Notification.create(
            recipient_id=recipient_id,
            sender_id=sender_id,
            event_type=EventType.COMMENT_POSTED,
            post_id=post_id,
            comment_id=comment_id,
        )
        saved = notification_repository.save(notification)

        saved.increment_attempt()
        saved.mark_failed("SMTP timeout")
        future = datetime.now(UTC) + timedelta(minutes=5)
        object.__setattr__(saved, "next_retry_at", future)
        updated = notification_repository.save(saved)

        assert updated.attempt_count == 1
        assert updated.status == NotificationStatus.FAILED
        assert getattr(updated, "next_retry_at") is not None

    def test_save_preserves_immutable_fields(
        self,
        test_user: tuple[User, int],
        test_sender: tuple[User, int],
        test_post: tuple[Post, int],
        test_comment: tuple[CommentModel, int],
        notification_repository: NotificationRepository,
    ) -> None:
        """Test that save does not alter created_at or recipient_id on update.

        Args:
            test_user: Tuple of recipient User and its database ID.
            test_sender: Tuple of sender User and its database ID.
            test_post: Tuple of Post and its database ID.
            test_comment: Tuple of CommentModel and its database ID.
            notification_repository: Repository under test.
        """
        _, recipient_id = test_user
        _, sender_id = test_sender
        _, post_id = test_post
        _, comment_id = test_comment
        notification = Notification.create(
            recipient_id=recipient_id,
            sender_id=sender_id,
            event_type=EventType.COMMENT_POSTED,
            post_id=post_id,
            comment_id=comment_id,
        )
        saved = notification_repository.save(notification)
        original_created_at = saved.created_at
        original_recipient_id = saved.recipient_id
        original_post_id = saved.post_id
        original_comment_id = saved.comment_id

        saved.mark_sent()
        updated = notification_repository.save(saved)

        assert updated.created_at == original_created_at
        assert updated.recipient_id == original_recipient_id
        assert updated.post_id == original_post_id
        assert updated.comment_id == original_comment_id

    def test_save_nonexistent_id_raises_valueerror(
        self,
        notification_repository: NotificationRepository,
    ) -> None:
        """Test that updating a Notification with an ID that doesn't exist
        in the database raises ValueError rather than silently no-oping.

        Args:
            notification_repository: Repository under test.
        """
        ghost = Notification(
            id=99999,
            recipient_id=1,
            sender_id=2,
            event_type=EventType.COMMENT_POSTED,
            post_id=1,
            comment_id=1,
            status=NotificationStatus.PENDING,
            attempt_count=0,
            created_at=datetime.now(UTC),
            sent_at=None,
            error_message=None,
            next_retry_at=None,
        )

        with pytest.raises(ValueError):
            notification_repository.save(ghost)


class TestGetById:
    """Test get_by_id query."""

    def test_gets_notification_by_id(
        self,
        test_user: tuple[User, int],
        test_sender: tuple[User, int],
        test_post: tuple[Post, int],
        test_comment: tuple[CommentModel, int],
        notification_repository: NotificationRepository,
    ) -> None:
        """Test get_by_id returns the correct Notification aggregate after save.

        Args:
            test_user: Tuple of recipient User and its database ID.
            test_sender: Tuple of sender User and its database ID.
            test_post: Tuple of Post and its database ID.
            test_comment: Tuple of CommentModel and its database ID.
            notification_repository: Repository under test.
        """
        _, recipient_id = test_user
        _, sender_id = test_sender
        _, post_id = test_post
        _, comment_id = test_comment
        notification = Notification.create(
            recipient_id=recipient_id,
            sender_id=sender_id,
            event_type=EventType.REPLY_RECEIVED,
            post_id=post_id,
            comment_id=comment_id,
        )
        saved = notification_repository.save(notification)
        assert saved.id is not None

        found = notification_repository.get_by_id(saved.id)

        assert found is not None
        assert found.id == saved.id
        assert found.recipient_id == recipient_id
        assert found.event_type == EventType.REPLY_RECEIVED

    def test_returns_none_for_missing_id(
        self,
        notification_repository: NotificationRepository,
    ) -> None:
        """Test that get_by_id returns None for a non-existent id.

        Args:
            notification_repository: Repository under test.
        """
        found = notification_repository.get_by_id(99999)

        assert found is None


class TestGetPending:
    """Test get_pending query filtering, ordering, and limit behaviour."""

    def test_gets_pending_notifications(
        self,
        test_user: tuple[User, int],
        test_sender: tuple[User, int],
        test_post: tuple[Post, int],
        test_comment: tuple[CommentModel, int],
        notification_repository: NotificationRepository,
    ) -> None:
        """Test that get_pending returns only PENDING status notifications.

        Args:
            test_user: Tuple of recipient User and its database ID.
            test_sender: Tuple of sender User and its database ID.
            test_post: Tuple of Post and its database ID.
            test_comment: Tuple of CommentModel and its database ID.
            notification_repository: Repository under test.
        """
        _, recipient_id = test_user
        _, sender_id = test_sender
        _, post_id = test_post
        _, comment_id = test_comment
        notification = Notification.create(
            recipient_id=recipient_id,
            sender_id=sender_id,
            event_type=EventType.COMMENT_POSTED,
            post_id=post_id,
            comment_id=comment_id,
        )
        notification_repository.save(notification)

        pending = notification_repository.get_pending()

        assert len(pending) == 1
        assert pending[0].status == NotificationStatus.PENDING

    def test_limits_results(
        self,
        session: Session,
        test_user: tuple[User, int],
        test_sender: tuple[User, int],
        test_post: tuple[Post, int],
        notification_repository: NotificationRepository,
    ) -> None:
        """Test that get_pending respects the limit parameter.

        Args:
            session: In-memory SQLite session.
            test_user: Tuple of recipient User and its database ID.
            test_sender: Tuple of sender User and its database ID.
            test_post: Tuple of Post and its database ID.
            notification_repository: Repository under test.
        """
        _, recipient_id = test_user
        _, author_id = test_user
        _, sender_id = test_sender
        _, post_id = test_post
        now = datetime.now(UTC)
        for i in range(3):
            comment = CommentModel(
                post_id=post_id,
                author_id=author_id,
                text=f"Comment {i}",
                created_at=now,
                updated_at=now,
            )
            session.add(comment)
            session.commit()
            session.refresh(comment)
            assert comment.id is not None
            notification = Notification.create(
                recipient_id=recipient_id,
                sender_id=sender_id,
                event_type=EventType.COMMENT_POSTED,
                post_id=post_id,
                comment_id=comment.id,
            )
            notification_repository.save(notification)

        pending = notification_repository.get_pending(limit=2)

        assert len(pending) == 2

    def test_excludes_non_pending_status(
        self,
        session: Session,
        test_user: tuple[User, int],
        test_sender: tuple[User, int],
        test_post: tuple[Post, int],
        notification_repository: NotificationRepository,
    ) -> None:
        """Test that SENT and FAILED notifications are excluded from
        get_pending.

        Args:
            session: In-memory SQLite session.
            test_user: Tuple of recipient User and its database ID.
            test_sender: Tuple of sender User and its database ID.
            test_post: Tuple of Post and its database ID.
            notification_repository: Repository under test.
        """
        _, recipient_id = test_user
        _, author_id = test_user
        _, sender_id = test_sender
        _, post_id = test_post
        now = datetime.now(UTC)

        for i, status in enumerate(
            [NotificationStatus.SENT, NotificationStatus.FAILED]
        ):
            comment = CommentModel(
                post_id=post_id,
                author_id=author_id,
                text=f"Non-pending comment {i}",
                created_at=now,
                updated_at=now,
            )
            session.add(comment)
            session.commit()
            session.refresh(comment)
            assert comment.id is not None
            notification = Notification.create(
                recipient_id=recipient_id,
                sender_id=sender_id,
                event_type=EventType.COMMENT_POSTED,
                post_id=post_id,
                comment_id=comment.id,
            )
            saved = notification_repository.save(notification)
            saved.status = status
            notification_repository.save(saved)

        pending = notification_repository.get_pending()

        assert len(pending) == 0

    def test_orders_by_created_at_desc(
        self,
        session: Session,
        test_user: tuple[User, int],
        test_sender: tuple[User, int],
        test_post: tuple[Post, int],
        notification_repository: NotificationRepository,
    ) -> None:
        """Test that get_pending returns notifications newest-first.

        Args:
            session: In-memory SQLite session.
            test_user: Tuple of recipient User and its database ID.
            test_sender: Tuple of sender User and its database ID.
            test_post: Tuple of Post and its database ID.
            notification_repository: Repository under test.
        """
        _, recipient_id = test_user
        _, author_id = test_user
        _, sender_id = test_sender
        _, post_id = test_post
        now = datetime.now(UTC)
        saved_ids: list[int] = []
        for i in range(2):
            comment = CommentModel(
                post_id=post_id,
                author_id=author_id,
                text=f"Ordered comment {i}",
                created_at=now,
                updated_at=now,
            )
            session.add(comment)
            session.commit()
            session.refresh(comment)
            assert comment.id is not None
            notification = Notification.create(
                recipient_id=recipient_id,
                sender_id=sender_id,
                event_type=EventType.COMMENT_POSTED,
                post_id=post_id,
                comment_id=comment.id,
            )
            saved = notification_repository.save(notification)
            assert saved.id is not None
            saved_ids.append(saved.id)

        pending = notification_repository.get_pending()

        assert pending[0].id == saved_ids[-1]
        assert pending[1].id == saved_ids[0]

    def test_respects_next_retry_at(
        self,
        session: Session,
        test_user: tuple[User, int],
        test_sender: tuple[User, int],
        test_post: tuple[Post, int],
        notification_repository: NotificationRepository,
    ) -> None:
        """Test that notifications with a future next_retry_at are excluded.

        Notifications with next_retry_at in the past or null must be included;
        those with a future value must be excluded.

        Args:
            session: In-memory SQLite session.
            test_user: Tuple of recipient User and its database ID.
            test_sender: Tuple of sender User and its database ID.
            test_post: Tuple of Post and its database ID.
            notification_repository: Repository under test.
        """
        _, recipient_id = test_user
        _, author_id = test_user
        _, sender_id = test_sender
        _, post_id = test_post
        now = datetime.now(UTC)

        comment_future = CommentModel(
            post_id=post_id,
            author_id=author_id,
            text="Future retry comment",
            created_at=now,
            updated_at=now,
        )
        comment_past = CommentModel(
            post_id=post_id,
            author_id=author_id,
            text="Past retry comment",
            created_at=now,
            updated_at=now,
        )
        session.add(comment_future)
        session.add(comment_past)
        session.commit()
        session.refresh(comment_future)
        session.refresh(comment_past)
        assert comment_future.id is not None
        assert comment_past.id is not None

        future_notification = Notification.create(
            recipient_id=recipient_id,
            sender_id=sender_id,
            event_type=EventType.COMMENT_POSTED,
            post_id=post_id,
            comment_id=comment_future.id,
        )
        past_notification = Notification.create(
            recipient_id=recipient_id,
            sender_id=sender_id,
            event_type=EventType.REPLY_RECEIVED,
            post_id=post_id,
            comment_id=comment_past.id,
        )

        saved_future = notification_repository.save(future_notification)
        saved_past = notification_repository.save(past_notification)
        assert saved_future.id is not None
        assert saved_past.id is not None

        future_time = datetime.now(UTC) + timedelta(hours=1)
        past_time = datetime.now(UTC) - timedelta(hours=1)
        notification_repository.mark_for_retry(saved_future.id, future_time)
        notification_repository.mark_for_retry(saved_past.id, past_time)

        pending = notification_repository.get_pending()

        pending_ids = [n.id for n in pending]
        assert saved_future.id not in pending_ids
        assert saved_past.id in pending_ids

    def test_default_limit_is_100(
        self,
        session: Session,
        test_user: tuple[User, int],
        test_sender: tuple[User, int],
        test_post: tuple[Post, int],
        notification_repository: NotificationRepository,
    ) -> None:
        """Test that get_pending defaults to returning at most 100 rows.

        Args:
            session: In-memory SQLite session.
            test_user: Tuple of recipient User and its database ID.
            test_sender: Tuple of sender User and its database ID.
            test_post: Tuple of Post and its database ID.
            notification_repository: Repository under test.
        """
        _, recipient_id = test_user
        _, author_id = test_user
        _, sender_id = test_sender
        _, post_id = test_post
        now = datetime.now(UTC)
        for i in range(101):
            comment = CommentModel(
                post_id=post_id,
                author_id=author_id,
                text=f"Bulk comment {i}",
                created_at=now,
                updated_at=now,
            )
            session.add(comment)
            session.commit()
            session.refresh(comment)
            assert comment.id is not None
            notification = Notification.create(
                recipient_id=recipient_id,
                sender_id=sender_id,
                event_type=EventType.COMMENT_POSTED,
                post_id=post_id,
                comment_id=comment.id,
            )
            notification_repository.save(notification)

        pending = notification_repository.get_pending()

        assert len(pending) == 100


class TestGetHistory:
    """Test get_history query for per-user notification history."""

    def test_gets_history_for_user(
        self,
        test_user: tuple[User, int],
        test_sender: tuple[User, int],
        test_post: tuple[Post, int],
        test_comment: tuple[CommentModel, int],
        notification_repository: NotificationRepository,
    ) -> None:
        """Test get_history returns notifications where recipient_id matches.

        Args:
            test_user: Tuple of recipient User and its database ID.
            test_sender: Tuple of sender User and its database ID.
            test_post: Tuple of Post and its database ID.
            test_comment: Tuple of CommentModel and its database ID.
            notification_repository: Repository under test.
        """
        _, recipient_id = test_user
        _, sender_id = test_sender
        _, post_id = test_post
        _, comment_id = test_comment
        notification = Notification.create(
            recipient_id=recipient_id,
            sender_id=sender_id,
            event_type=EventType.COMMENT_POSTED,
            post_id=post_id,
            comment_id=comment_id,
        )
        notification_repository.save(notification)

        history = notification_repository.get_history(recipient_id)

        assert len(history) == 1
        assert history[0].recipient_id == recipient_id

    def test_pagination_with_skip_and_limit(
        self,
        session: Session,
        test_user: tuple[User, int],
        test_sender: tuple[User, int],
        test_post: tuple[Post, int],
        notification_repository: NotificationRepository,
    ) -> None:
        """Test get_history respects skip and limit pagination parameters.

        Args:
            session: In-memory SQLite session.
            test_user: Tuple of recipient User and its database ID.
            test_sender: Tuple of sender User and its database ID.
            test_post: Tuple of Post and its database ID.
            notification_repository: Repository under test.
        """
        _, recipient_id = test_user
        _, author_id = test_user
        _, sender_id = test_sender
        _, post_id = test_post
        now = datetime.now(UTC)
        for i in range(5):
            comment = CommentModel(
                post_id=post_id,
                author_id=author_id,
                text=f"History comment {i}",
                created_at=now,
                updated_at=now,
            )
            session.add(comment)
            session.commit()
            session.refresh(comment)
            assert comment.id is not None
            notification = Notification.create(
                recipient_id=recipient_id,
                sender_id=sender_id,
                event_type=EventType.COMMENT_POSTED,
                post_id=post_id,
                comment_id=comment.id,
            )
            notification_repository.save(notification)

        page = notification_repository.get_history(
            recipient_id, skip=2, limit=2
        )

        assert len(page) == 2

    def test_orders_by_created_at_desc(
        self,
        session: Session,
        test_user: tuple[User, int],
        test_sender: tuple[User, int],
        test_post: tuple[Post, int],
        notification_repository: NotificationRepository,
    ) -> None:
        """Test get_history returns notifications in descending
        created_at order.

        Args:
            session: In-memory SQLite session.
            test_user: Tuple of recipient User and its database ID.
            test_sender: Tuple of sender User and its database ID.
            test_post: Tuple of Post and its database ID.
            notification_repository: Repository under test.
        """
        _, recipient_id = test_user
        _, author_id = test_user
        _, sender_id = test_sender
        _, post_id = test_post
        now = datetime.now(UTC)
        saved_ids: list[int] = []
        for i in range(2):
            comment = CommentModel(
                post_id=post_id,
                author_id=author_id,
                text=f"Desc ordered comment {i}",
                created_at=now,
                updated_at=now,
            )
            session.add(comment)
            session.commit()
            session.refresh(comment)
            assert comment.id is not None
            notification = Notification.create(
                recipient_id=recipient_id,
                sender_id=sender_id,
                event_type=EventType.COMMENT_POSTED,
                post_id=post_id,
                comment_id=comment.id,
            )
            saved = notification_repository.save(notification)
            assert saved.id is not None
            saved_ids.append(saved.id)

        history = notification_repository.get_history(recipient_id)

        assert history[0].id == saved_ids[-1]
        assert history[1].id == saved_ids[0]


class TestMarkForRetry:
    """Test mark_for_retry scheduling method."""

    def test_updates_next_retry_at(
        self,
        test_user: tuple[User, int],
        test_sender: tuple[User, int],
        test_post: tuple[Post, int],
        test_comment: tuple[CommentModel, int],
        notification_repository: NotificationRepository,
        session: Session,
    ) -> None:
        """Test that mark_for_retry sets next_retry_at on the persisted row.

        Args:
            test_user: Tuple of recipient User and its database ID.
            test_sender: Tuple of sender User and its database ID.
            test_post: Tuple of Post and its database ID.
            test_comment: Tuple of CommentModel and its database ID.
            notification_repository: Repository under test.
            session: In-memory SQLite session.
        """
        _, recipient_id = test_user
        _, sender_id = test_sender
        _, post_id = test_post
        _, comment_id = test_comment
        notification = Notification.create(
            recipient_id=recipient_id,
            sender_id=sender_id,
            event_type=EventType.COMMENT_POSTED,
            post_id=post_id,
            comment_id=comment_id,
        )
        saved = notification_repository.save(notification)
        assert saved.id is not None
        retry_at = datetime.now(UTC) + timedelta(minutes=30)

        notification_repository.mark_for_retry(saved.id, retry_at)

        row = session.exec(
            select(NotificationModel).where(NotificationModel.id == saved.id)
        ).first()
        assert row is not None
        assert row.next_retry_at is not None

    def test_preserves_pending_status(
        self,
        test_user: tuple[User, int],
        test_sender: tuple[User, int],
        test_post: tuple[Post, int],
        test_comment: tuple[CommentModel, int],
        notification_repository: NotificationRepository,
        session: Session,
    ) -> None:
        """Test that mark_for_retry leaves status as PENDING so the notification
        remains eligible for get_pending() once next_retry_at has passed.

        Args:
            test_user: Tuple of recipient User and its database ID.
            test_sender: Tuple of sender User and its database ID.
            test_post: Tuple of Post and its database ID.
            test_comment: Tuple of CommentModel and its database ID.
            notification_repository: Repository under test.
            session: In-memory SQLite session.
        """
        _, recipient_id = test_user
        _, sender_id = test_sender
        _, post_id = test_post
        _, comment_id = test_comment
        notification = Notification.create(
            recipient_id=recipient_id,
            sender_id=sender_id,
            event_type=EventType.COMMENT_POSTED,
            post_id=post_id,
            comment_id=comment_id,
        )
        saved = notification_repository.save(notification)
        assert saved.id is not None
        retry_at = datetime.now(UTC) + timedelta(minutes=30)

        notification_repository.mark_for_retry(saved.id, retry_at)

        row = session.exec(
            select(NotificationModel).where(NotificationModel.id == saved.id)
        ).first()
        assert row is not None
        assert row.status == NotificationStatus.PENDING

    def test_preserves_created_at(
        self,
        test_user: tuple[User, int],
        test_sender: tuple[User, int],
        test_post: tuple[Post, int],
        test_comment: tuple[CommentModel, int],
        notification_repository: NotificationRepository,
        session: Session,
    ) -> None:
        """Test that mark_for_retry does not modify created_at.

        Args:
            test_user: Tuple of recipient User and its database ID.
            test_sender: Tuple of sender User and its database ID.
            test_post: Tuple of Post and its database ID.
            test_comment: Tuple of CommentModel and its database ID.
            notification_repository: Repository under test.
            session: In-memory SQLite session.
        """
        _, recipient_id = test_user
        _, sender_id = test_sender
        _, post_id = test_post
        _, comment_id = test_comment
        notification = Notification.create(
            recipient_id=recipient_id,
            sender_id=sender_id,
            event_type=EventType.COMMENT_POSTED,
            post_id=post_id,
            comment_id=comment_id,
        )
        saved = notification_repository.save(notification)
        assert saved.id is not None
        original_created_at = saved.created_at
        retry_at = datetime.now(UTC) + timedelta(minutes=30)

        notification_repository.mark_for_retry(saved.id, retry_at)

        row = session.exec(
            select(NotificationModel).where(NotificationModel.id == saved.id)
        ).first()
        assert row is not None
        assert row.created_at == original_created_at.replace(tzinfo=None)


class TestCountPending:
    """Test count_pending aggregate query."""

    def test_count_pending(
        self,
        session: Session,
        test_user: tuple[User, int],
        test_sender: tuple[User, int],
        test_post: tuple[Post, int],
        notification_repository: NotificationRepository,
    ) -> None:
        """Test count_pending returns the number of PENDING notifications only.

        Args:
            session: In-memory SQLite session.
            test_user: Tuple of recipient User and its database ID.
            test_sender: Tuple of sender User and its database ID.
            test_post: Tuple of Post and its database ID.
            notification_repository: Repository under test.
        """
        _, recipient_id = test_user
        _, author_id = test_user
        _, sender_id = test_sender
        _, post_id = test_post
        now = datetime.now(UTC)

        for i in range(2):
            comment = CommentModel(
                post_id=post_id,
                author_id=author_id,
                text=f"Pending count comment {i}",
                created_at=now,
                updated_at=now,
            )
            session.add(comment)
            session.commit()
            session.refresh(comment)
            assert comment.id is not None
            notification = Notification.create(
                recipient_id=recipient_id,
                sender_id=sender_id,
                event_type=EventType.COMMENT_POSTED,
                post_id=post_id,
                comment_id=comment.id,
            )
            notification_repository.save(notification)

        sent_comment = CommentModel(
            post_id=post_id,
            author_id=author_id,
            text="Sent count comment",
            created_at=now,
            updated_at=now,
        )
        session.add(sent_comment)
        session.commit()
        session.refresh(sent_comment)
        assert sent_comment.id is not None
        sent_notification = Notification.create(
            recipient_id=recipient_id,
            sender_id=sender_id,
            event_type=EventType.COMMENT_POSTED,
            post_id=post_id,
            comment_id=sent_comment.id,
        )
        saved_sent = notification_repository.save(sent_notification)
        saved_sent.mark_sent()
        notification_repository.save(saved_sent)

        count = notification_repository.count_pending()

        assert count == 2

    def test_excludes_sent_and_failed(
        self,
        session: Session,
        test_user: tuple[User, int],
        test_sender: tuple[User, int],
        test_post: tuple[Post, int],
        notification_repository: NotificationRepository,
    ) -> None:
        """Test count_pending ignores SENT and FAILED rows.

        Args:
            session: In-memory SQLite session.
            test_user: Tuple of recipient User and its database ID.
            test_sender: Tuple of sender User and its database ID.
            test_post: Tuple of Post and its database ID.
            notification_repository: Repository under test.
        """
        _, recipient_id = test_user
        _, author_id = test_user
        _, sender_id = test_sender
        _, post_id = test_post
        now = datetime.now(UTC)

        sent_comment = CommentModel(
            post_id=post_id,
            author_id=author_id,
            text="Sent for pending exclusion test",
            created_at=now,
            updated_at=now,
        )
        session.add(sent_comment)
        session.commit()
        session.refresh(sent_comment)
        assert sent_comment.id is not None
        sent_notif = Notification.create(
            recipient_id=recipient_id,
            sender_id=sender_id,
            event_type=EventType.COMMENT_POSTED,
            post_id=post_id,
            comment_id=sent_comment.id,
        )
        saved_sent = notification_repository.save(sent_notif)
        saved_sent.mark_sent()
        notification_repository.save(saved_sent)

        failed_comment = CommentModel(
            post_id=post_id,
            author_id=author_id,
            text="Failed for pending exclusion test",
            created_at=now,
            updated_at=now,
        )
        session.add(failed_comment)
        session.commit()
        session.refresh(failed_comment)
        assert failed_comment.id is not None
        failed_notif = Notification.create(
            recipient_id=recipient_id,
            sender_id=sender_id,
            event_type=EventType.REPLY_RECEIVED,
            post_id=post_id,
            comment_id=failed_comment.id,
        )
        saved_failed = notification_repository.save(failed_notif)
        saved_failed.mark_failed("error")
        notification_repository.save(saved_failed)

        count = notification_repository.count_pending()

        assert count == 0


class TestCountFailed:
    """Test count_failed aggregate query."""

    def test_count_failed(
        self,
        session: Session,
        test_user: tuple[User, int],
        test_sender: tuple[User, int],
        test_post: tuple[Post, int],
        notification_repository: NotificationRepository,
    ) -> None:
        """Test count_failed returns the number of FAILED notifications only.

        Args:
            session: In-memory SQLite session.
            test_user: Tuple of recipient User and its database ID.
            test_sender: Tuple of sender User and its database ID.
            test_post: Tuple of Post and its database ID.
            notification_repository: Repository under test.
        """
        _, recipient_id = test_user
        _, author_id = test_user
        _, sender_id = test_sender
        _, post_id = test_post
        now = datetime.now(UTC)

        failed_comment = CommentModel(
            post_id=post_id,
            author_id=author_id,
            text="Failed count comment",
            created_at=now,
            updated_at=now,
        )
        session.add(failed_comment)
        session.commit()
        session.refresh(failed_comment)
        assert failed_comment.id is not None
        failed_notification = Notification.create(
            recipient_id=recipient_id,
            sender_id=sender_id,
            event_type=EventType.COMMENT_POSTED,
            post_id=post_id,
            comment_id=failed_comment.id,
        )
        saved_failed = notification_repository.save(failed_notification)
        saved_failed.mark_failed("Delivery failed")
        notification_repository.save(saved_failed)

        for i in range(2):
            comment = CommentModel(
                post_id=post_id,
                author_id=author_id,
                text=f"Pending for failed count {i}",
                created_at=now,
                updated_at=now,
            )
            session.add(comment)
            session.commit()
            session.refresh(comment)
            assert comment.id is not None
            notification = Notification.create(
                recipient_id=recipient_id,
                sender_id=sender_id,
                event_type=EventType.REPLY_RECEIVED,
                post_id=post_id,
                comment_id=comment.id,
            )
            notification_repository.save(notification)

        count = notification_repository.count_failed()

        assert count == 1

    def test_excludes_pending_and_sent(
        self,
        session: Session,
        test_user: tuple[User, int],
        test_sender: tuple[User, int],
        test_post: tuple[Post, int],
        notification_repository: NotificationRepository,
    ) -> None:
        """Test count_failed ignores PENDING and SENT rows.

        Args:
            session: In-memory SQLite session.
            test_user: Tuple of recipient User and its database ID.
            test_sender: Tuple of sender User and its database ID.
            test_post: Tuple of Post and its database ID.
            notification_repository: Repository under test.
        """
        _, recipient_id = test_user
        _, author_id = test_user
        _, sender_id = test_sender
        _, post_id = test_post
        now = datetime.now(UTC)

        pending_comment = CommentModel(
            post_id=post_id,
            author_id=author_id,
            text="Pending for failed exclusion test",
            created_at=now,
            updated_at=now,
        )
        session.add(pending_comment)
        session.commit()
        session.refresh(pending_comment)
        assert pending_comment.id is not None
        notification_repository.save(
            Notification.create(
                recipient_id=recipient_id,
                sender_id=sender_id,
                event_type=EventType.COMMENT_POSTED,
                post_id=post_id,
                comment_id=pending_comment.id,
            )
        )

        sent_comment = CommentModel(
            post_id=post_id,
            author_id=author_id,
            text="Sent for failed exclusion test",
            created_at=now,
            updated_at=now,
        )
        session.add(sent_comment)
        session.commit()
        session.refresh(sent_comment)
        assert sent_comment.id is not None
        sent_notif = Notification.create(
            recipient_id=recipient_id,
            sender_id=sender_id,
            event_type=EventType.REPLY_RECEIVED,
            post_id=post_id,
            comment_id=sent_comment.id,
        )
        saved_sent = notification_repository.save(sent_notif)
        saved_sent.mark_sent()
        notification_repository.save(saved_sent)

        count = notification_repository.count_failed()

        assert count == 0


class TestConstraints:
    """Test database-level constraints on NotificationModel."""

    def test_unique_constraint_comment_event_recipient(
        self,
        test_user: tuple[User, int],
        test_sender: tuple[User, int],
        test_post: tuple[Post, int],
        test_comment: tuple[CommentModel, int],
        notification_repository: NotificationRepository,
    ) -> None:
        """Test that duplicate (comment_id, event_type, recipient_id)
        raises IntegrityError.

        Args:
            test_user: Tuple of recipient User and its database ID.
            test_sender: Tuple of sender User and its database ID.
            test_post: Tuple of Post and its database ID.
            test_comment: Tuple of CommentModel and its database ID.
            notification_repository: Repository under test.
        """
        _, recipient_id = test_user
        _, sender_id = test_sender
        _, post_id = test_post
        _, comment_id = test_comment
        first = Notification.create(
            recipient_id=recipient_id,
            sender_id=sender_id,
            event_type=EventType.COMMENT_POSTED,
            post_id=post_id,
            comment_id=comment_id,
        )
        notification_repository.save(first)

        duplicate = Notification.create(
            recipient_id=recipient_id,
            sender_id=sender_id,
            event_type=EventType.COMMENT_POSTED,
            post_id=post_id,
            comment_id=comment_id,
        )

        with pytest.raises(IntegrityError):
            notification_repository.save(duplicate)

    def test_foreign_key_recipient_id_enforced(
        self,
        session: Session,
        test_sender: tuple[User, int],
        test_post: tuple[Post, int],
        test_comment: tuple[CommentModel, int],
    ) -> None:
        """Test that an invalid recipient_id FK raises IntegrityError.

        Args:
            session: In-memory SQLite session.
            test_sender: Tuple of sender User and its database ID.
            test_post: Tuple of Post and its database ID.
            test_comment: Tuple of CommentModel and its database ID.
        """
        session.connection().execute(text("PRAGMA foreign_keys=ON"))
        _, sender_id = test_sender
        _, post_id = test_post
        _, comment_id = test_comment

        row = NotificationModel(
            recipient_id=99999,
            sender_id=sender_id,
            event_type=EventType.COMMENT_POSTED,
            post_id=post_id,
            comment_id=comment_id,
            status="pending",
        )
        session.add(row)

        with pytest.raises(IntegrityError):
            session.commit()

    def test_foreign_key_sender_id_enforced(
        self,
        session: Session,
        test_user: tuple[User, int],
        test_post: tuple[Post, int],
        test_comment: tuple[CommentModel, int],
    ) -> None:
        """Test that an invalid sender_id FK raises IntegrityError.

        Args:
            session: In-memory SQLite session.
            test_user: Tuple of recipient User and its database ID.
            test_post: Tuple of Post and its database ID.
            test_comment: Tuple of CommentModel and its database ID.
        """
        session.connection().execute(text("PRAGMA foreign_keys=ON"))
        _, recipient_id = test_user
        _, post_id = test_post
        _, comment_id = test_comment

        row = NotificationModel(
            recipient_id=recipient_id,
            sender_id=99999,
            event_type=EventType.COMMENT_POSTED,
            post_id=post_id,
            comment_id=comment_id,
            status="pending",
        )
        session.add(row)

        with pytest.raises(IntegrityError):
            session.commit()


class TestIndexes:
    """Test that required database indexes exist on the notifications table."""

    def test_index_status_created_exists(self, session: Session) -> None:
        """Test that idx_notification_status_created index exists.

        Args:
            session: In-memory SQLite session.
        """
        inspector = sa_inspect(session.get_bind())
        indexes = {
            idx["name"] for idx in inspector.get_indexes("notifications")
        }

        assert "idx_notification_status_created" in indexes

    def test_index_recipient_created_exists(self, session: Session) -> None:
        """Test that idx_notification_recipient_created index exists.

        Args:
            session: In-memory SQLite session.
        """
        inspector = sa_inspect(session.get_bind())
        indexes = {
            idx["name"] for idx in inspector.get_indexes("notifications")
        }

        assert "idx_notification_recipient_created" in indexes

    def test_index_next_retry_exists(self, session: Session) -> None:
        """Test that idx_notification_next_retry index exists.

        Args:
            session: In-memory SQLite session.
        """
        inspector = sa_inspect(session.get_bind())
        indexes = {
            idx["name"] for idx in inspector.get_indexes("notifications")
        }

        assert "idx_notification_next_retry" in indexes
