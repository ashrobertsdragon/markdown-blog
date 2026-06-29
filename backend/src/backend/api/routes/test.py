"""Test-only endpoints for seeding and resetting state in acceptance tests.

Only active when FLASK_ENV=TESTING. Returns 404 in all other environments.
"""

import os
import uuid
from datetime import UTC, datetime

from flask import Blueprint, Response, jsonify, request
from sqlalchemy import delete
from sqlmodel import Session, SQLModel, select

from backend.application.commands.handlers.process_notifications_handler import (  # noqa: E501
    handle_process_notifications,
)
from backend.application.commands.process_notifications_command import (
    ProcessNotificationsCommand,
)
from backend.config import FileSystemSettings
from backend.domain.value_objects.unsubscribe_token import UnsubscribeToken
from backend.infrastructure.email.email_sender import EmailSender
from backend.infrastructure.email.resend_email_service import ResendEmailService
from backend.infrastructure.persistence.comment_repository import (
    CommentRepository,
)
from backend.infrastructure.persistence.database import get_engine
from backend.infrastructure.persistence.filesystem_draft_repository import (
    DraftFile,
    FileSystemDraftRepository,
)
from backend.infrastructure.persistence.models import (
    CommentModel,
    NotificationModel,
    Post,
    PostRevisionModel,
    User,
    UserNotificationPreferencesModel,
)
from backend.infrastructure.persistence.notification_repository import (
    NotificationRepository,
)
from backend.infrastructure.persistence.post_repository import PostRepository
from backend.infrastructure.persistence.user_repository import UserRepository

test_bp = Blueprint("test", __name__)

_TEST_SLUGS = [
    "test-post",
    "publish-me",
    "delete-me",
    "draft-1",
    "pub-1",
]


def _guard() -> tuple[Response, int] | None:
    """Return 404 response if not running in TESTING mode."""
    if os.environ.get("FLASK_ENV") != "TESTING":
        return jsonify({"error": "Not found"}), 404
    return None


def _get_draft_repo() -> FileSystemDraftRepository:
    """Return a FileSystemDraftRepository for the configured DRAFTS_PATH."""
    settings = FileSystemSettings()
    return FileSystemDraftRepository(settings.DRAFTS_PATH)


@test_bp.route("/seed", methods=["POST"])
def seed() -> tuple[Response, int]:
    """Create test users, posts, comments, and draft files for acceptance tests.

    Drops and recreates all tables on every call to guarantee a clean
    state regardless of prior test run outcome. Creates two users
    (author + admin), DB post records, matching filesystem draft files,
    and seeded comments on test-post for comment acceptance tests.

    Returns:
        201 with seeded entity counts on success.
        404 if not running in TESTING mode.
    """
    guard = _guard()
    if guard is not None:
        return guard

    from backend.api.routes.comments import _get_rate_limit_service

    _get_rate_limit_service().clear()

    engine = get_engine()

    from sqlalchemy import text

    with engine.connect() as conn:
        conn.execute(text("PRAGMA foreign_keys = OFF;"))

    SQLModel.metadata.drop_all(engine)
    SQLModel.metadata.create_all(engine)

    body = request.get_json(silent=True) or {}
    author_clerk_id = body.get("author_clerk_id", "user_test_author")
    admin_clerk_id = body.get("admin_clerk_id", "user_test_admin")
    user_clerk_id = body.get("user_clerk_id", "user_test_user")

    now = datetime.now(UTC)
    with Session(engine) as session:
        author = User(
            email="author@example.com",
            role="author",
            clerk_user_id=author_clerk_id,
        )
        admin = User(
            email="admin@example.com",
            role="admin",
            clerk_user_id=admin_clerk_id,
        )
        regular_user = User(
            email="user@example.com",
            role="authenticated",
            clerk_user_id=user_clerk_id,
        )
        session.add(author)
        session.add(admin)
        session.add(regular_user)
        session.flush()

        posts_specs = [
            ("test-post", "Test Post", "<h1>Initial Content</h1>", True),
            ("publish-me", "Publish Me", "<p>Draft content</p>", False),
            ("delete-me", "Delete Me", "<p>To be deleted</p>", False),
            ("draft-1", "Draft 1", "", False),
            ("pub-1", "Published 1", "<p>Published content</p>", True),
        ]
        for slug, title, html, published in posts_specs:
            session.add(
                Post(
                    slug=slug,
                    title=title,
                    html_content=html,
                    published=published,
                    published_at=now if published else None,
                    author_id=author.id,
                )
            )

        session.flush()

        test_post = session.exec(
            select(Post).where(Post.slug == "test-post")
        ).first()
        if test_post:
            assert test_post.id is not None
            assert author.id is not None
            revisions = [
                PostRevisionModel(
                    id=uuid.uuid4(),
                    post_id=test_post.id,
                    commit_sha="c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2",
                    author_id=author.id,
                    commit_message="Revert to initial",
                    markdown_content="# Initial Content\n\nTest content.",
                    is_revert=True,
                    created_at=datetime(2026, 2, 21, 12, 0, 0, tzinfo=UTC),
                    updated_at=datetime(2026, 2, 21, 12, 0, 0, tzinfo=UTC),
                ),
                PostRevisionModel(
                    id=uuid.uuid4(),
                    post_id=test_post.id,
                    commit_sha="b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1",
                    author_id=author.id,
                    commit_message="Update content",
                    markdown_content="# Updated Content\n\nMore test content.",
                    is_revert=False,
                    created_at=datetime(2026, 2, 21, 11, 0, 0, tzinfo=UTC),
                    updated_at=datetime(2026, 2, 21, 11, 0, 0, tzinfo=UTC),
                ),
                PostRevisionModel(
                    id=uuid.uuid4(),
                    post_id=test_post.id,
                    commit_sha="a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0",
                    author_id=author.id,
                    commit_message="Initial post draft",
                    markdown_content="# Initial Content\n\nTest content.",
                    is_revert=False,
                    created_at=datetime(2026, 2, 21, 10, 0, 0, tzinfo=UTC),
                    updated_at=datetime(2026, 2, 21, 10, 0, 0, tzinfo=UTC),
                ),
            ]
            for rev in revisions:
                session.add(rev)

            seed_comment = CommentModel(
                post_id=test_post.id,
                author_id=author.id,
                parent_id=None,
                text="A seeded comment for acceptance tests",
                created_at=datetime(2026, 3, 1, 10, 0, 0, tzinfo=UTC),
                updated_at=datetime(2026, 3, 1, 10, 0, 0, tzinfo=UTC),
                is_deleted=False,
                is_pending_moderation=False,
            )
            session.add(seed_comment)
            session.flush()
            assert seed_comment.id is not None

            seed_reply = CommentModel(
                post_id=test_post.id,
                author_id=author.id,
                parent_id=seed_comment.id,
                text="@comment1 A seeded reply for acceptance tests",
                created_at=datetime(2026, 3, 1, 10, 5, 0, tzinfo=UTC),
                updated_at=datetime(2026, 3, 1, 10, 5, 0, tzinfo=UTC),
                is_deleted=False,
                is_pending_moderation=False,
            )
            session.add(seed_reply)

        session.commit()
        users_count = len(session.exec(select(User)).all())
        posts_count = len(session.exec(select(Post)).all())
        revisions_count = len(session.exec(select(PostRevisionModel)).all())

    draft_repo = _get_draft_repo()
    draft_specs = [
        ("test-post", "Test Post", "# Initial Content\n\nTest content.", True),
        ("publish-me", "Publish Me", "# Publish Me\n\nDraft content.", False),
        ("delete-me", "Delete Me", "# Delete Me\n\nTo be deleted.", False),
        ("draft-1", "Draft 1", "# Draft 1\n\nDraft content.", False),
        ("pub-1", "Published 1", "# Published 1\n\nPublished content.", True),
    ]
    for slug, title, content, published in draft_specs:
        draft_repo.save(
            DraftFile(
                slug=slug,
                title=title,
                author=author_clerk_id,
                content=content,
                published=published,
                created_at=now,
            )
        )

    return jsonify(
        {
            "status": "seeded",
            "users": users_count,
            "posts": posts_count,
            "revisions": revisions_count,
        }
    ), 201


@test_bp.route("/reset", methods=["DELETE"])
def reset() -> tuple[Response, int]:
    """Delete all test data from the database and filesystem.

    Truncates Post and User tables and removes test draft files so each
    test suite starts clean.

    Returns:
        200 on success.
        404 if not running in TESTING mode.
    """
    guard = _guard()
    if guard is not None:
        return guard

    engine = get_engine()
    with Session(engine) as session:
        session.exec(delete(PostRevisionModel))
        session.exec(delete(Post))
        session.exec(delete(User))
        session.commit()

    draft_repo = _get_draft_repo()
    for slug in _TEST_SLUGS:
        draft_repo.delete(slug)

    return jsonify({"status": "reset"}), 200


class _StubResendEmailService(ResendEmailService):
    """Stub email service for E2E tests that avoids real HTTP calls.

    Returns deterministic fake email IDs so tests can assert that
    notifications were processed without hitting the Resend API.
    """

    def __init__(self) -> None:
        """Initialise with a placeholder key — no real API calls are made."""
        super().__init__(api_key="test-key-stub")

    def send_template(
        self,
        to: str,
        template_id: str,
        variables: dict[str, str],
    ) -> str | None:
        """Return a fake Resend email ID without making an HTTP request."""
        return f"test-email-{uuid.uuid4()}"


@test_bp.route("/notifications", methods=["GET"])
def list_notifications() -> tuple[Response, int]:
    """Return all notification records for a given post slug.

    Used by E2E tests to assert that comment events created notification
    records with the expected status and metadata.

    Query parameters:
        post_slug: Slug of the post to filter notifications by.

    Returns:
        200 with {notifications: [...]} on success.
        400 if post_slug is missing.
        404 if not running in TESTING mode or post not found.
    """
    guard = _guard()
    if guard is not None:
        return guard

    post_slug = request.args.get("post_slug")
    if not post_slug:
        return jsonify({"error": "post_slug query parameter is required"}), 400

    engine = get_engine()
    with Session(engine) as session:
        post = session.exec(select(Post).where(Post.slug == post_slug)).first()
        if post is None:
            return jsonify({"error": f"Post '{post_slug}' not found"}), 404

        notifications = session.exec(
            select(NotificationModel).where(
                NotificationModel.post_id == post.id
            )
        ).all()

        payload = [
            {
                "id": n.id,
                "recipient_id": n.recipient_id,
                "sender_id": n.sender_id,
                "event_type": n.event_type,
                "post_id": n.post_id,
                "comment_id": n.comment_id,
                "status": n.status,
                "attempt_count": n.attempt_count,
                "created_at": n.created_at.isoformat()
                if n.created_at
                else None,
                "sent_at": n.sent_at.isoformat() if n.sent_at else None,
                "error_message": n.error_message,
                "resend_email_id": getattr(n, "resend_email_id", None),
            }
            for n in notifications
        ]

    return jsonify({"notifications": payload}), 200


@test_bp.route("/process-notifications", methods=["POST"])
def process_notifications() -> tuple[Response, int]:
    """Synchronously run the notification processing job for E2E tests.

    Wires up real repositories with a stub email service that returns
    fake Resend email IDs instead of making live HTTP requests.

    Returns:
        200 with {sent, failed, total} summary on success.
        404 if not running in TESTING mode.
    """
    guard = _guard()
    if guard is not None:
        return guard

    command = ProcessNotificationsCommand(
        batch_limit=100,
        max_retries=3,
        site_base_url="http://localhost:5555",
    )
    summary = handle_process_notifications(
        command=command,
        notification_repo=NotificationRepository(),
        email_sender=EmailSender(service=_StubResendEmailService()),
        post_repo=PostRepository(),
        comment_repo=CommentRepository(),
        user_repo=UserRepository(),
    )
    return jsonify(summary), 200


@test_bp.route("/unsubscribe-token", methods=["GET"])
def generate_unsubscribe_token() -> tuple[Response, int]:
    """Generate a valid HMAC unsubscribe token for a seeded test user.

    Looks up the user by id and generates a token using the same logic
    as production so E2E tests can construct valid unsubscribe URLs.

    Query parameters:
        user_id: Integer primary key of the user.

    Returns:
        200 with {user_id, token} on success.
        400 if user_id is missing or invalid.
        404 if not running in TESTING mode or user not found.
    """
    guard = _guard()
    if guard is not None:
        return guard

    raw_id = request.args.get("user_id")
    if not raw_id:
        return jsonify({"error": "user_id query parameter is required"}), 400

    try:
        user_id = int(raw_id)
    except ValueError:
        return jsonify({"error": "user_id must be an integer"}), 400

    engine = get_engine()
    with Session(engine) as session:
        user = session.exec(select(User).where(User.id == user_id)).first()
        if user is None:
            return jsonify({"error": f"User {user_id} not found"}), 404
        email = user.email

    token = UnsubscribeToken.generate(user_id, email)
    return jsonify({"user_id": user_id, "token": token.value}), 200


@test_bp.route("/user-preferences", methods=["GET"])
def get_user_preferences() -> tuple[Response, int]:
    """Return notification preferences for a test user without authentication.

    Looks up the user by clerk_user_id query parameter. Returns default values
    (all true) if no preference row exists yet.

    Query parameters:
        clerk_user_id: Clerk identifier of the user to look up.

    Returns:
        200 with {notify_on_comment_replies, notify_on_mentions,
        notify_on_new_posts} on success.
        400 if clerk_user_id is missing.
        404 if not running in TESTING mode or user not found.
    """
    guard = _guard()
    if guard is not None:
        return guard

    clerk_user_id = request.args.get("clerk_user_id")
    if not clerk_user_id:
        return jsonify(
            {"error": "clerk_user_id query parameter is required"}
        ), 400

    engine = get_engine()
    with Session(engine) as session:
        user = session.exec(
            select(User).where(User.clerk_user_id == clerk_user_id)
        ).first()
        if user is None:
            return jsonify({"error": f"User '{clerk_user_id}' not found"}), 404

        assert user.id is not None
        prefs = session.exec(
            select(UserNotificationPreferencesModel).where(
                UserNotificationPreferencesModel.user_id == user.id
            )
        ).first()

        if prefs is None:
            return jsonify(
                {
                    "notify_on_comment_replies": True,
                    "notify_on_mentions": True,
                    "notify_on_new_posts": True,
                }
            ), 200

        return jsonify(
            {
                "notify_on_comment_replies": prefs.notify_on_comment_replies,
                "notify_on_mentions": prefs.notify_on_mentions,
                "notify_on_new_posts": prefs.notify_on_new_posts,
            }
        ), 200


@test_bp.route("/user-preferences", methods=["PUT"])
def set_user_preferences() -> tuple[Response, int]:
    """Directly update notification preferences for a test user.

    Bypasses authentication so E2E tests can configure preference state
    without navigating the UI. Looks up the user by clerk_user_id and
    upserts the UserNotificationPreferencesModel row.

    Request body (JSON):
        clerk_user_id: Clerk identifier of the user to update.
        notify_on_comment_replies: bool (optional).
        notify_on_mentions: bool (optional).
        notify_on_new_posts: bool (optional).

    Returns:
        200 with updated preferences on success.
        400 if clerk_user_id is missing.
        404 if not running in TESTING mode or user not found.
    """
    guard = _guard()
    if guard is not None:
        return guard

    body = request.get_json(silent=True) or {}
    clerk_user_id = body.get("clerk_user_id")
    if not clerk_user_id:
        return jsonify({"error": "clerk_user_id is required"}), 400

    engine = get_engine()
    with Session(engine) as session:
        user = session.exec(
            select(User).where(User.clerk_user_id == clerk_user_id)
        ).first()
        if user is None:
            return jsonify({"error": f"User '{clerk_user_id}' not found"}), 404

        assert user.id is not None
        prefs = session.exec(
            select(UserNotificationPreferencesModel).where(
                UserNotificationPreferencesModel.user_id == user.id
            )
        ).first()

        if prefs is None:
            prefs = UserNotificationPreferencesModel(user_id=user.id)
            session.add(prefs)

        if "notify_on_comment_replies" in body:
            prefs.notify_on_comment_replies = bool(
                body["notify_on_comment_replies"]
            )
        if "notify_on_mentions" in body:
            prefs.notify_on_mentions = bool(body["notify_on_mentions"])
        if "notify_on_new_posts" in body:
            prefs.notify_on_new_posts = bool(body["notify_on_new_posts"])

        prefs.updated_at = datetime.now(UTC)
        session.commit()
        session.refresh(prefs)

        return (
            jsonify(
                {
                    "user_id": user.id,
                    "notify_on_comment_replies": (
                        prefs.notify_on_comment_replies
                    ),
                    "notify_on_mentions": prefs.notify_on_mentions,
                    "notify_on_new_posts": prefs.notify_on_new_posts,
                }
            ),
            200,
        )
