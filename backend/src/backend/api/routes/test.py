"""Test-only endpoints for seeding and resetting state in acceptance tests.

Only active when FLASK_ENV=TESTING. Returns 404 in all other environments.
"""

import os

from flask import Blueprint, Response, jsonify
from sqlalchemy import delete
from sqlmodel import Session

from backend.infrastructure.persistence.database import get_engine
from backend.infrastructure.persistence.models import Post, User

test_bp = Blueprint("test", __name__)


def _guard() -> tuple[Response, int] | None:
    """Return 404 response if not running in TESTING mode."""
    if os.environ.get("FLASK_ENV") != "TESTING":
        return jsonify({"error": "Not found"}), 404
    return None


@test_bp.route("/seed", methods=["POST"])
def seed() -> tuple[Response, int]:
    """Create test users and posts for acceptance tests.

    Creates two users (author + admin) and a set of posts with
    known slugs that the post-management acceptance tests expect.

    Returns:
        201 with seeded entity counts on success.
        404 if not running in TESTING mode.
    """
    guard = _guard()
    if guard is not None:
        return guard

    engine = get_engine()
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

    return jsonify({"status": "seeded", "users": 2, "posts": len(posts)}), 201


@test_bp.route("/reset", methods=["DELETE"])
def reset() -> tuple[Response, int]:
    """Delete all test data from the database.

    Truncates Post and User tables so each test suite starts clean.

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

    return jsonify({"status": "reset"}), 200
