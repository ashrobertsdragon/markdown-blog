"""Test-only endpoints for seeding and resetting state in acceptance tests.

Only active when FLASK_ENV=TESTING. Returns 404 in all other environments.
"""

import os
import uuid
from datetime import UTC, datetime

from flask import Blueprint, Response, jsonify
from sqlalchemy import delete
from sqlmodel import Session, SQLModel, select

from backend.config import FileSystemSettings
from backend.infrastructure.persistence.database import get_engine
from backend.infrastructure.persistence.filesystem_draft_repository import (
    DraftFile,
    FileSystemDraftRepository,
)
from backend.infrastructure.persistence.models import (
    CommentModel,
    Post,
    PostRevisionModel,
    User,
)

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

    now = datetime.now(UTC)
    with Session(engine) as session:
        author = User(
            email="author@example.com",
            role="author",
            clerk_user_id="user_test_author",
        )
        admin = User(
            email="admin@example.com",
            role="admin",
            clerk_user_id="user_test_admin",
        )
        session.add(author)
        session.add(admin)
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
                author="user_test_author",
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
