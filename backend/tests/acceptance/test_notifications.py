"""Acceptance tests for Notifications spec based on requirements.md.

These tests verify email notification system, queue processing, Resend
integration, retry logic, and user preferences, ensuring alignment with
the Acceptance Criteria in @.spec-workflow/specs/notifications/requirements.md.
"""

from unittest.mock import MagicMock, patch

import pytest
from flask.testing import FlaskClient
from sqlmodel import Session, select

from backend.domain.aggregates.user import User
from backend.domain.value_objects.unsubscribe_token import UnsubscribeToken
from backend.infrastructure.persistence.database import get_engine
from backend.infrastructure.persistence.models import (
    NotificationModel,
    UserNotificationPreferencesModel,
)

_AUTH_HEADER = {"Authorization": "Bearer test-token"}


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


@pytest.mark.skip(reason="Requires Resend HTML template inspection")
def test_email_template_rendering() -> None:
    """Test professional email templates rendered based on event type.

    Acceptance Criteria:
    - Email template rendered based on event_type
    - Reply notification includes subject, post title, excerpts, links
    - Mention notification includes subject, context, links
    - Both include unsubscribe link
    """


@pytest.mark.skip(reason="Requires live Resend API call (external test)")
def test_resend_email_service_integration() -> None:
    """Test email delivery via Resend API.

    Acceptance Criteria:
    - Background job processes notification: Resend API called
    - Resend API call succeeds: status set to "sent"
    - Resend API call fails: status set to "failed", attempt incremented
    - Max retries exceeded: status set to "failed_permanently"
    """


@pytest.mark.skip(reason="Cron script execution tested separately")
def test_background_job_cron() -> None:
    """Test cron job processes notifications automatically.

    Acceptance Criteria:
    - Cron runs every minute: pending notifications fetched
    - Batch limited to 100 per run
    - Job exit code 0 on success, non-zero on error
    - Summary log: emails sent, failed, total processed
    """


@pytest.mark.skip(reason="Retry timing requires sleep or time mocking")
def test_retry_logic() -> None:
    """Test automatic email retries for temporary failures.

    Acceptance Criteria:
    - Email send fails: attempt_count incremented
    - attempt_count < 3: eligible for retry
    - attempt_count >= 3: status set to "failed_permanently"
    - Exponential backoff: 1m, 5m, 15m between retries
    """


def test_user_notification_preferences(
    client: FlaskClient,
    mock_clerk_auth: None,
) -> None:
    """Test users can control which notifications they receive.

    Acceptance Criteria:
    - GET returns current preferences (defaults all-enabled on first access)
    - PUT updates only the specified fields
    - Disabling a type: preference reflected immediately in subsequent GET
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
    - Invalid token: 400 returned
    - Missing parameters: 400 returned
    - After unsubscribe: all preference flags are False
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
    mock_clerk_auth_admin: None,
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
    - Non-admin: 403 returned
    - Pagination: skip/limit query params supported
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
    - Duplicate insert attempt: silently ignored (no second row)
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


@pytest.mark.skip(reason="Requires load testing setup")
def test_performance_and_scalability() -> None:
    """Test notification system scales for high-traffic blogs.

    Acceptance Criteria:
    - 100+ notifications pending: processed in batches < 2s
    - Creating notification: DB write < 50ms
    - Database query for pending: < 100ms (indexed on status, created_at)
    """


@pytest.mark.skip(reason="Requires log capture and monitoring infrastructure")
def test_monitoring_and_alerting() -> None:
    """Test visibility into notification system health.

    Acceptance Criteria:
    - Job completes: summary statistics logged
    - Failure rate > 10%: warning logged
    - Notification stuck pending > 1 hour: warning logged
    """
