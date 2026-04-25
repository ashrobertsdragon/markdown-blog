"""Acceptance tests for Notifications spec based on requirements.md.

These tests verify email notification system, queue processing, Resend
integration, retry logic, and user preferences, ensuring alignment with
the Acceptance Criteria in @.spec-workflow/specs/notifications/requirements.md.
"""

import time
import uuid
from datetime import UTC, datetime, timedelta
from typing import cast
from unittest.mock import MagicMock, patch

import pytest
from flask.testing import FlaskClient
from sqlmodel import Session, select

from backend.application.commands.handlers.process_notifications_handler import (
    handle_process_notifications,
)
from backend.application.commands.process_notifications_command import (
    ProcessNotificationsCommand,
)
from backend.domain.aggregates.user import User
from backend.domain.value_objects.unsubscribe_token import UnsubscribeToken
from backend.infrastructure.email.email_sender import EmailSender
from backend.infrastructure.email.resend_email_service import ResendEmailService
from backend.infrastructure.monitoring.notification_metrics import (
    NotificationMetrics,
)
from backend.infrastructure.persistence.comment_repository import (
    CommentRepository,
)
from backend.infrastructure.persistence.database import get_engine
from backend.infrastructure.persistence.models import (
    NotificationModel,
    UserNotificationPreferencesModel,
)
from backend.infrastructure.persistence.models import User as UserModel
from backend.infrastructure.persistence.notification_repository import (
    NotificationRepository,
)
from backend.infrastructure.persistence.post_repository import PostRepository
from backend.infrastructure.persistence.user_repository import UserRepository

_AUTH_HEADER = {"Authorization": "Bearer test-token"}


@pytest.fixture
def seeded_users(author_user: User, reader_user: User) -> None:
    """Insert real User rows so UserRepository.find_by_id() can locate them.

    The mock-auth fixtures return User domain objects with id=10 and id=20
    but never write rows to the database. The notification handler does a
    real DB lookup, so tests that invoke the handler directly need rows.
    """
    with Session(get_engine()) as session:
        for u in (author_user, reader_user):
            assert u.id is not None
            session.add(
                UserModel(
                    id=u.id,
                    email=u.email,
                    role=u.role.value,
                    clerk_user_id=u.clerk_user_id,
                )
            )
        session.commit()


class _StubEmailService(ResendEmailService):
    """Stub that records calls without hitting the Resend API."""

    def __init__(self) -> None:
        """Initialise with a placeholder key."""
        super().__init__(api_key="test-key-stub")
        self.calls: list[dict[str, object]] = []

    def send_template(
        self, to: str, template_id: str, variables: dict[str, str]
    ) -> str | None:
        """Record the call and return a fake email ID."""
        self.calls.append(
            {"to": to, "template_id": template_id, "variables": variables}
        )
        return f"test-email-{uuid.uuid4()}"


class _FailingEmailService(ResendEmailService):
    """Stub that always fails to deliver email."""

    def __init__(self) -> None:
        """Initialise with a placeholder key."""
        super().__init__(api_key="test-key-stub")

    def send_template(
        self, to: str, template_id: str, variables: dict[str, str]
    ) -> str | None:
        """Simulate delivery failure by returning None."""
        return None


def _make_command(max_retries: int = 3) -> ProcessNotificationsCommand:
    """Return a ProcessNotificationsCommand wired for tests."""
    return ProcessNotificationsCommand(
        batch_limit=100,
        max_retries=max_retries,
        site_base_url="http://localhost:5555",
    )


def _run_with_stub(stub: ResendEmailService) -> dict[str, int]:
    """Run the handler with a given email stub and return the summary."""
    return handle_process_notifications(
        command=_make_command(),
        notification_repo=NotificationRepository(),
        email_sender=EmailSender(service=stub),
        post_repo=PostRepository(),
        comment_repo=CommentRepository(),
        user_repo=UserRepository(),
    )


def test_notification_queue(
    client: FlaskClient,
    published_post: str,
    mock_clerk_auth: None,
    auth_context,
    reader_user: User,
    reader_jwt_payload: dict[str, object],
) -> None:
    """Test notifications queued in database for async processing.

    Acceptance Criteria:
    - Event triggers notification: Notification record created in database
    - Status defaults to "pending"
    - Notification has: recipient_id, event_type, post_id, comment_id,
      sender_id, created_at
    - Pending notifications available for background job processing
    """
    slug = published_post

    with auth_context(reader_user, reader_jwt_payload):
        resp = client.post(
            f"/api/posts/{slug}/comments",
            headers=_AUTH_HEADER,
            json={"text": "A comment that triggers a notification."},
        )
    assert resp.status_code == 201
    comment_id = resp.json["id"]

    with Session(get_engine()) as session:
        notifications = session.exec(
            select(NotificationModel).where(
                NotificationModel.comment_id == comment_id
            )
        ).all()

    assert len(notifications) >= 1
    n = notifications[0]
    assert n.status == "pending"
    assert n.event_type in ("comment_posted", "reply_received")
    assert n.post_id is not None
    assert n.comment_id == comment_id
    assert n.sender_id is not None
    assert n.created_at is not None

    pending = NotificationRepository().get_pending()
    pending_ids = [p.id for p in pending]
    assert n.id in pending_ids


def test_email_template_rendering(
    client: FlaskClient,
    published_post: str,
    mock_clerk_auth: None,
    seeded_users: None,
    auth_context,
    reader_user: User,
    reader_jwt_payload: dict[str, object],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test template variables are built correctly per event type.

    Acceptance Criteria:
    - Email template rendered based on event_type
    - Reply notification variables include REPLY_AUTHOR, POST_TITLE,
      ORIGINAL_COMMENT, REPLY_EXCERPT, POST_URL, UNSUBSCRIBE_URL
    - Mention notification variables include MENTION_AUTHOR, POST_TITLE,
      MENTION_CONTEXT, POST_URL, UNSUBSCRIBE_URL
    - Plain comment notification uses the reply template
    - Email rendered and delivered (stub confirms send_template called)
    """
    monkeypatch.setenv("SECRET_KEY", "test-secret-key-for-templates")
    slug = published_post

    with auth_context(reader_user, reader_jwt_payload):
        resp = client.post(
            f"/api/posts/{slug}/comments",
            headers=_AUTH_HEADER,
            json={"text": "Comment for template rendering test."},
        )
    assert resp.status_code == 201

    stub = _StubEmailService()
    summary = _run_with_stub(stub)

    assert summary["sent"] >= 1
    assert len(stub.calls) >= 1

    call = stub.calls[0]
    variables = call["variables"]
    assert isinstance(variables, dict)
    assert "POST_URL" in variables
    assert "UNSUBSCRIBE_URL" in variables
    assert "POST_TITLE" in variables
    assert call["template_id"] != ""

    reply_resp = client.post(
        f"/api/posts/{slug}/comments/{resp.json['id']}/reply",
        headers=_AUTH_HEADER,
        json={"text": "@reader This is a reply."},
    )
    assert reply_resp.status_code == 201

    stub2 = _StubEmailService()
    monkeypatch.setenv("SECRET_KEY", "test-secret-key-for-templates")
    _run_with_stub(stub2)

    reply_calls = [
        c
        for c in stub2.calls
        if "REPLY_EXCERPT" in cast(dict[str, str], c["variables"])
    ]
    assert len(reply_calls) >= 1
    rv = cast(dict[str, str], reply_calls[0]["variables"])
    assert "REPLY_AUTHOR" in rv
    assert "POST_TITLE" in rv
    assert "REPLY_EXCERPT" in rv
    assert "POST_URL" in rv
    assert "UNSUBSCRIBE_URL" in rv


def test_resend_email_service_integration(
    client: FlaskClient,
    published_post: str,
    mock_clerk_auth: None,
    seeded_users: None,
    auth_context,
    reader_user: User,
    reader_jwt_payload: dict[str, object],
) -> None:
    """Test end-to-end processing: pending notification → sent via stub.

    Acceptance Criteria:
    - Background job processes notification: email sender called
    - Notification.status set to "sent" on success
    - sent_at timestamp recorded
    - Summary counts are accurate
    """
    slug = published_post

    with auth_context(reader_user, reader_jwt_payload):
        resp = client.post(
            f"/api/posts/{slug}/comments",
            headers=_AUTH_HEADER,
            json={"text": "Comment to trigger email send."},
        )
    assert resp.status_code == 201
    comment_id = resp.json["id"]

    process_resp = client.post("/api/test/process-notifications")
    assert process_resp.status_code == 200
    summary = process_resp.json
    assert summary["sent"] >= 1
    assert summary["total"] >= 1
    assert summary["failed"] == 0

    with Session(get_engine()) as session:
        n = session.exec(
            select(NotificationModel).where(
                NotificationModel.comment_id == comment_id
            )
        ).first()

    assert n is not None
    assert n.status == "sent"
    assert n.sent_at is not None


def test_background_job_cron(
    client: FlaskClient,
    published_post: str,
    mock_clerk_auth: None,
    seeded_users: None,
    auth_context,
    reader_user: User,
    reader_jwt_payload: dict[str, object],
) -> None:
    """Test the processing job handles a batch of pending notifications.

    Acceptance Criteria:
    - Cron job fetches pending notifications, processes them
    - All pending notifications processed in one run
    - Summary log: emails sent, failed, total processed
    - Job summary counts exactly match processed count
    """
    slug = published_post

    with auth_context(reader_user, reader_jwt_payload):
        for i in range(3):
            r = client.post(
                f"/api/posts/{slug}/comments",
                headers=_AUTH_HEADER,
                json={"text": f"Batch comment {i}."},
            )
            assert r.status_code == 201

    with Session(get_engine()) as session:
        pending_before = session.exec(
            select(NotificationModel).where(
                NotificationModel.status == "pending"
            )
        ).all()
    pending_count = len(pending_before)
    assert pending_count >= 3

    process_resp = client.post("/api/test/process-notifications")
    assert process_resp.status_code == 200
    summary = process_resp.json
    assert summary["total"] == pending_count
    assert summary["sent"] == pending_count
    assert summary["failed"] == 0

    with Session(get_engine()) as session:
        remaining_pending = session.exec(
            select(NotificationModel).where(
                NotificationModel.status == "pending"
            )
        ).all()
    assert len(remaining_pending) == 0


def test_retry_logic(
    client: FlaskClient,
    published_post: str,
    mock_clerk_auth: None,
    seeded_users: None,
    auth_context,
    reader_user: User,
    reader_jwt_payload: dict[str, object],
) -> None:
    """Test exponential backoff retry and permanent failure after max retries.

    Acceptance Criteria:
    - Email send fails: attempt_count incremented
    - attempt_count < max_retries: next_retry_at scheduled (not None)
    - attempt_count >= max_retries: status set to "failed" permanently
    """
    slug = published_post

    with auth_context(reader_user, reader_jwt_payload):
        resp = client.post(
            f"/api/posts/{slug}/comments",
            headers=_AUTH_HEADER,
            json={"text": "Comment for retry logic test."},
        )
    assert resp.status_code == 201
    comment_id = resp.json["id"]

    failing = _FailingEmailService()
    summary1 = _run_with_stub(failing)
    assert summary1["failed"] >= 1

    with Session(get_engine()) as session:
        n1 = session.exec(
            select(NotificationModel).where(
                NotificationModel.comment_id == comment_id
            )
        ).first()
    assert n1 is not None
    assert n1.attempt_count == 1
    assert n1.status == "pending"
    assert n1.next_retry_at is not None

    with Session(get_engine()) as session:
        model = session.exec(
            select(NotificationModel).where(
                NotificationModel.comment_id == comment_id
            )
        ).first()
        assert model is not None
        model.next_retry_at = datetime.now(UTC) - timedelta(seconds=1)
        session.commit()

    _run_with_stub(failing)

    with Session(get_engine()) as session:
        n2 = session.exec(
            select(NotificationModel).where(
                NotificationModel.comment_id == comment_id
            )
        ).first()
    assert n2 is not None
    assert n2.attempt_count == 2
    assert n2.status == "pending"

    with Session(get_engine()) as session:
        model = session.exec(
            select(NotificationModel).where(
                NotificationModel.comment_id == comment_id
            )
        ).first()
        assert model is not None
        model.next_retry_at = datetime.now(UTC) - timedelta(seconds=1)
        session.commit()

    _run_with_stub(failing)

    with Session(get_engine()) as session:
        n3 = session.exec(
            select(NotificationModel).where(
                NotificationModel.comment_id == comment_id
            )
        ).first()
    assert n3 is not None
    assert n3.attempt_count == 3
    assert n3.status == "failed"
    assert n3.error_message is not None


def test_user_notification_preferences(
    client: FlaskClient,
    mock_clerk_auth: None,
) -> None:
    """Test users can control which notifications they receive.

    Acceptance Criteria:
    - GET returns current preferences (defaults all-enabled on first access)
    - PUT updates only the specified fields
    - Disabling a type: preference reflected immediately in subsequent GET
    - Unauthenticated: 401
    """
    get_resp = client.get(
        "/api/user/notification-preferences",
        headers=_AUTH_HEADER,
    )
    assert get_resp.status_code == 200
    prefs = get_resp.json["preferences"]
    assert prefs["notify_on_comment_replies"] is True
    assert prefs["notify_on_mentions"] is True
    assert prefs["notify_on_new_posts"] is True

    put_resp = client.put(
        "/api/user/notification-preferences",
        headers=_AUTH_HEADER,
        json={"notify_on_comment_replies": False},
    )
    assert put_resp.status_code == 200
    updated = put_resp.json["preferences"]
    assert updated["notify_on_comment_replies"] is False
    assert updated["notify_on_mentions"] is True

    get_resp2 = client.get(
        "/api/user/notification-preferences",
        headers=_AUTH_HEADER,
    )
    assert get_resp2.status_code == 200
    assert get_resp2.json["preferences"]["notify_on_comment_replies"] is False

    unauth_resp = client.get("/api/user/notification-preferences")
    assert unauth_resp.status_code == 401


def test_unsubscribe_functionality(
    client: FlaskClient,
    mock_clerk_auth: None,
    author_user: User,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test users can unsubscribe from emails.

    Acceptance Criteria:
    - Valid token: preferences updated to all disabled, 200 returned
    - After unsubscribe: all preference flags are False
    - Invalid token: 400 returned
    - Missing parameters: 400 returned
    """
    monkeypatch.setenv("SECRET_KEY", "test-secret-key-for-unsubscribe")
    assert author_user.id is not None

    mock_user_repo = MagicMock()
    mock_user_repo.find_by_id.return_value = author_user

    token = UnsubscribeToken.generate(
        user_id=author_user.id,
        email=author_user.email,
    )

    with patch(
        "backend.api.routes.notifications._get_user_repository",
        return_value=mock_user_repo,
    ):
        resp = client.get(
            "/api/unsubscribe",
            query_string={
                "user_id": author_user.id,
                "token": token.value,
            },
        )
        assert resp.status_code == 200
        assert "unsubscribed" in resp.json["message"].lower()

        with Session(get_engine()) as session:
            prefs = session.exec(
                select(UserNotificationPreferencesModel).where(
                    UserNotificationPreferencesModel.user_id == author_user.id
                )
            ).first()

        assert prefs is not None
        assert prefs.notify_on_comment_replies is False
        assert prefs.notify_on_mentions is False
        assert prefs.notify_on_new_posts is False

        bad_token_resp = client.get(
            "/api/unsubscribe",
            query_string={
                "user_id": author_user.id,
                "token": "a" * 64,
            },
        )
        assert bad_token_resp.status_code == 400

    missing_resp = client.get("/api/unsubscribe")
    assert missing_resp.status_code == 400


def test_notification_history(
    client: FlaskClient,
    published_post: str,
    mock_clerk_auth: None,
    auth_context,
    admin_user: User,
    admin_jwt_payload: dict[str, object],
    reader_user: User,
    reader_jwt_payload: dict[str, object],
) -> None:
    """Test admins can view notification history for debugging.

    Acceptance Criteria:
    - Admin GET /api/admin/notifications: all notifications listed
    - Each entry shows: recipient_id, event_type, status, created_at
    - Pagination with skip/limit works
    - Non-admin: 403 returned
    """
    slug = published_post

    with auth_context(reader_user, reader_jwt_payload):
        client.post(
            f"/api/posts/{slug}/comments",
            headers=_AUTH_HEADER,
            json={"text": "Comment that creates a notification."},
        )

    with auth_context(admin_user, admin_jwt_payload):
        resp = client.get(
            "/api/admin/notifications",
            headers=_AUTH_HEADER,
        )

    assert resp.status_code == 200
    data = resp.json
    assert "notifications" in data
    assert "total" in data
    assert data["total"] >= 1

    n = data["notifications"][0]
    assert "event_type" in n
    assert "status" in n
    assert "created_at" in n
    assert "recipient_id" in n

    with auth_context(admin_user, admin_jwt_payload):
        paginated = client.get(
            "/api/admin/notifications?skip=0&limit=1",
            headers=_AUTH_HEADER,
        )
    assert paginated.status_code == 200
    assert len(paginated.json["notifications"]) <= 1

    with auth_context(reader_user, reader_jwt_payload):
        forbidden_resp = client.get(
            "/api/admin/notifications",
            headers=_AUTH_HEADER,
        )
    assert forbidden_resp.status_code == 403


def test_event_triggers(
    client: FlaskClient,
    published_post: str,
    mock_clerk_auth: None,
    auth_context,
    reader_user: User,
    reader_jwt_payload: dict[str, object],
) -> None:
    """Test events create appropriate notifications.

    Acceptance Criteria:
    - CommentPosted: post author receives notification record (if enabled)
    - ReplyReceived: original commenter receives notification record
    - Notification record created immediately on event
    - Both events create distinct notification rows with correct event_type
    """
    slug = published_post

    with auth_context(reader_user, reader_jwt_payload):
        comment_resp = client.post(
            f"/api/posts/{slug}/comments",
            headers=_AUTH_HEADER,
            json={"text": "Original comment."},
        )
    assert comment_resp.status_code == 201
    comment_id = comment_resp.json["id"]

    with Session(get_engine()) as session:
        comment_notifications = session.exec(
            select(NotificationModel).where(
                NotificationModel.comment_id == comment_id
            )
        ).all()
    assert len(comment_notifications) >= 1
    event_types = {n.event_type for n in comment_notifications}
    assert "comment_posted" in event_types

    reply_resp = client.post(
        f"/api/posts/{slug}/comments/{comment_id}/reply",
        headers=_AUTH_HEADER,
        json={"text": "@reader This is a reply."},
    )
    assert reply_resp.status_code == 201
    reply_id = reply_resp.json["id"]

    with Session(get_engine()) as session:
        reply_notifications = session.exec(
            select(NotificationModel).where(
                NotificationModel.comment_id == reply_id
            )
        ).all()
    assert len(reply_notifications) >= 1
    reply_event_types = {n.event_type for n in reply_notifications}
    assert "reply_received" in reply_event_types


def test_notification_deduplication(
    client: FlaskClient,
    published_post: str,
    mock_clerk_auth: None,
    auth_context,
    reader_user: User,
    reader_jwt_payload: dict[str, object],
) -> None:
    """Test duplicate notifications are prevented.

    Acceptance Criteria:
    - Same comment_id + event_type + recipient_id: only one notification row
    - Unique constraint enforced at database level
    """
    slug = published_post

    with auth_context(reader_user, reader_jwt_payload):
        resp = client.post(
            f"/api/posts/{slug}/comments",
            headers=_AUTH_HEADER,
            json={"text": "Comment for deduplication test."},
        )
    assert resp.status_code == 201
    comment_id = resp.json["id"]

    with Session(get_engine()) as session:
        notifications = session.exec(
            select(NotificationModel).where(
                NotificationModel.comment_id == comment_id,
                NotificationModel.event_type == "comment_posted",
            )
        ).all()

    recipient_ids = [n.recipient_id for n in notifications]
    assert len(recipient_ids) == len(set(recipient_ids)), (
        "Duplicate notifications found for same recipient+comment+event_type"
    )


def test_performance_and_scalability(
    client: FlaskClient,
    published_post: str,
    mock_clerk_auth: None,
    seeded_users: None,
    auth_context,
    reader_user: User,
    reader_jwt_payload: dict[str, object],
) -> None:
    """Test notification processing handles a realistic batch efficiently.

    Acceptance Criteria:
    - Multiple pending notifications processed in one job run
    - All notifications reach terminal state (sent)
    - Processing completes in reasonable time
    """
    slug = published_post
    count = 5

    with auth_context(reader_user, reader_jwt_payload):
        for i in range(count):
            r = client.post(
                f"/api/posts/{slug}/comments",
                headers=_AUTH_HEADER,
                json={"text": f"Perf test comment {i}."},
            )
            assert r.status_code == 201

    start = time.monotonic()
    process_resp = client.post("/api/test/process-notifications")
    elapsed = time.monotonic() - start

    assert process_resp.status_code == 200
    summary = process_resp.json
    assert summary["total"] == count
    assert summary["sent"] == count
    assert elapsed < 10.0


def test_monitoring_and_alerting(
    client: FlaskClient,
    published_post: str,
    mock_clerk_auth: None,
    seeded_users: None,
    auth_context,
    reader_user: User,
    reader_jwt_payload: dict[str, object],
) -> None:
    """Test notification health metrics and alerting logic.

    Acceptance Criteria:
    - Metrics calculate failure rate correctly
    - Stuck notifications (pending > 1 hour) detected
    - Health summary includes sent, failed, pending, failure_rate, stuck_count
    """
    slug = published_post

    with auth_context(reader_user, reader_jwt_payload):
        for i in range(2):
            client.post(
                f"/api/posts/{slug}/comments",
                headers=_AUTH_HEADER,
                json={"text": f"Monitoring test comment {i}."},
            )

    client.post("/api/test/process-notifications")

    with Session(get_engine()) as session:
        first = session.exec(select(NotificationModel)).first()
        assert first is not None
        first.status = "failed"
        session.commit()

    with Session(get_engine()) as session:
        old_notification = session.exec(
            select(NotificationModel).where(NotificationModel.status == "sent")
        ).first()
        if old_notification is None:
            pending = session.exec(select(NotificationModel)).first()
            assert pending is not None
            old_notification = pending

        old_notification.status = "pending"
        old_notification.next_retry_at = None
        old_notification.created_at = datetime.now(UTC) - timedelta(hours=2)
        session.commit()

    metrics = NotificationMetrics(NotificationRepository())
    summary = metrics.get_health_summary(stuck_hours=1)

    assert "sent" in summary
    assert "failed" in summary
    assert "pending" in summary
    assert "failure_rate" in summary
    assert "stuck_count" in summary
    assert "timestamp" in summary

    assert summary["failed"] >= 1
    assert summary["failure_rate"] > 0.0
    assert summary["stuck_count"] >= 1
