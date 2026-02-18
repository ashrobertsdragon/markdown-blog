"""Test-only endpoints for seeding and resetting state in acceptance tests.

Only active when FLASK_ENV=TESTING. Returns 404 in all other environments.
"""

import os
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
from backend.infrastructure.persistence.models import Post, User

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
    """Create test users, posts, and draft files for acceptance tests.

    Drops and recreates all tables on every call to guarantee a clean
    state regardless of prior test run outcome. Creates two users
    (author + admin), DB post records, and matching filesystem draft
    files with known slugs that post-management tests expect.

    Returns:
        201 with seeded entity counts on success.
        404 if not running in TESTING mode.
    """
    guard = _guard()
    if guard is not None:
        return guard

    engine = get_engine()
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

        posts = [
            Post(
                slug="test-post",
                title="Test Post",
                html_content="<h1>Initial Content</h1>",
                published=False,
                author_id=author.id,
            ),
            Post(
                slug="publish-me",
                title="Publish Me",
                html_content="<p>Draft content</p>",
                published=False,
                author_id=author.id,
            ),
            Post(
                slug="delete-me",
                title="Delete Me",
                html_content="<p>To be deleted</p>",
                published=False,
                author_id=author.id,
            ),
            Post(
                slug="draft-1",
                title="Draft 1",
                html_content="",
                published=False,
                author_id=author.id,
            ),
            Post(
                slug="pub-1",
                title="Published 1",
                html_content="<p>Published content</p>",
                published=True,
                author_id=author.id,
            ),
        ]
        for post in posts:
            session.add(post)

        session.commit()
        users_count = len(session.exec(select(User)).all())
        posts_count = len(session.exec(select(Post)).all())

    draft_repo = _get_draft_repo()
    draft_specs = [
        ("test-post", "Test Post", "# Initial Content\n\nTest content.", False),
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
        {"status": "seeded", "users": users_count, "posts": posts_count}
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
        session.exec(delete(Post))
        session.exec(delete(User))
        session.commit()

    draft_repo = _get_draft_repo()
    for slug in _TEST_SLUGS:
        draft_repo.delete(slug)

    return jsonify({"status": "reset"}), 200
