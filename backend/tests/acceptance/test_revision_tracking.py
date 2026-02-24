"""Acceptance tests for Revision Tracking spec based on requirements.md.

These tests verify revision history display, diff viewer, revert operations,
and permission controls using the test seed endpoint for data and real HS256
JWT tokens for authentication. No mocking of application components.
"""

import os

import jwt
import pytest
from flask.testing import FlaskClient

_SHA_NEWEST = "c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2"
_SHA_MIDDLE = "b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1"
_SHA_OLDEST = "a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0"
_TEST_SLUG = "test-post"
_FAR_FUTURE_EXP = 9999999999


def _make_token(sub: str, email: str) -> str:
    """Generate an HS256 JWT signed with the active test CLERK_SECRET_KEY.

    Reads the secret at call time so the test environment monkeypatch
    has already set it before this function executes.
    """
    return jwt.encode(
        {"sub": sub, "email": email, "exp": _FAR_FUTURE_EXP},
        os.environ.get("CLERK_SECRET_KEY", ""),
        algorithm="HS256",
    )


def _author_token() -> str:
    """Return a JWT for the seeded author user."""
    return _make_token("user_test_author", "author@example.com")


def _admin_token() -> str:
    """Return a JWT for the seeded admin user."""
    return _make_token("user_test_admin", "admin@example.com")


def _other_token() -> str:
    """Return a JWT for a user that is not the post owner."""
    return _make_token("user_other_999", "other@example.com")


@pytest.fixture
def seeded(client: FlaskClient) -> FlaskClient:
    """Seed the database with users, posts, and revisions.

    Seeds via the test endpoint which drops and recreates all tables,
    then inserts two users (author, admin) and five posts. Three
    revisions are created for 'test-post' with known SHAs.
    """
    resp = client.post("/api/test/seed")
    assert resp.status_code == 201
    return client


def test_revision_timeline_lists_all_commits(seeded: FlaskClient) -> None:
    """Listing revisions returns all stored commits for the post."""
    resp = seeded.get(
        f"/api/posts/{_TEST_SLUG}/revisions",
        headers={"Authorization": f"Bearer {_author_token()}"},
    )

    assert resp.status_code == 200
    body = resp.json
    assert "revisions" in body
    assert "total_count" in body
    assert "has_more" in body
    assert body["total_count"] == 3
    assert len(body["revisions"]) == 3


def test_revision_timeline_ordered_most_recent_first(
    seeded: FlaskClient,
) -> None:
    """Revisions are returned with the most recent commit appearing first."""
    resp = seeded.get(
        f"/api/posts/{_TEST_SLUG}/revisions",
        headers={"Authorization": f"Bearer {_author_token()}"},
    )

    assert resp.status_code == 200
    shas = [r["commit_sha"] for r in resp.json["revisions"]]
    assert shas == [_SHA_NEWEST, _SHA_MIDDLE, _SHA_OLDEST]


def test_revision_entry_includes_required_metadata(
    seeded: FlaskClient,
) -> None:
    """Each revision exposes commit SHA, author, timestamp, and message."""
    resp = seeded.get(
        f"/api/posts/{_TEST_SLUG}/revisions",
        headers={"Authorization": f"Bearer {_author_token()}"},
    )

    assert resp.status_code == 200
    revision = resp.json["revisions"][0]
    assert "commit_sha" in revision
    assert "author_id" in revision
    assert "commit_message" in revision
    assert "created_at" in revision or "timestamp" in revision


def test_pagination_returns_limited_revisions(seeded: FlaskClient) -> None:
    """A limit of 1 returns one revision and signals more exist."""
    resp = seeded.get(
        f"/api/posts/{_TEST_SLUG}/revisions?skip=0&limit=1",
        headers={"Authorization": f"Bearer {_author_token()}"},
    )

    assert resp.status_code == 200
    assert len(resp.json["revisions"]) == 1
    assert resp.json["has_more"] is True


def test_pagination_skip_advances_offset(seeded: FlaskClient) -> None:
    """Skipping the first two revisions returns only the oldest."""
    resp = seeded.get(
        f"/api/posts/{_TEST_SLUG}/revisions?skip=2&limit=10",
        headers={"Authorization": f"Bearer {_author_token()}"},
    )

    assert resp.status_code == 200
    revisions = resp.json["revisions"]
    assert len(revisions) == 1
    assert revisions[0]["commit_sha"] == _SHA_OLDEST


def test_pagination_limit_below_minimum_returns_error(
    seeded: FlaskClient,
) -> None:
    """A limit of 0 is rejected with a 400 error."""
    resp = seeded.get(
        f"/api/posts/{_TEST_SLUG}/revisions?limit=0",
        headers={"Authorization": f"Bearer {_author_token()}"},
    )

    assert resp.status_code == 400
    assert "error" in resp.json


def test_view_revision_at_specific_sha(seeded: FlaskClient) -> None:
    """Fetching a revision by SHA returns its stored content and metadata."""
    resp = seeded.get(
        f"/api/posts/{_TEST_SLUG}/revisions/{_SHA_OLDEST}",
        headers={"Authorization": f"Bearer {_author_token()}"},
    )

    assert resp.status_code == 200
    body = resp.json
    assert body["commit_sha"] == _SHA_OLDEST
    assert "short_sha" in body
    assert "author_id" in body
    assert "timestamp" in body
    assert "commit_message" in body
    assert "markdown_content" in body
    assert "html_content" in body
    assert "is_revert" in body
    assert body["is_revert"] is False


def test_view_revert_revision_is_flagged(seeded: FlaskClient) -> None:
    """A revision that was created by a revert has is_revert set to True."""
    resp = seeded.get(
        f"/api/posts/{_TEST_SLUG}/revisions/{_SHA_NEWEST}",
        headers={"Authorization": f"Bearer {_author_token()}"},
    )

    assert resp.status_code == 200
    assert resp.json["is_revert"] is True


def test_view_revision_for_unknown_sha_returns_not_found(
    seeded: FlaskClient,
) -> None:
    """Requesting a non-existent SHA returns 404."""
    unknown = "0000000000000000000000000000000000000000"

    resp = seeded.get(
        f"/api/posts/{_TEST_SLUG}/revisions/{unknown}",
        headers={"Authorization": f"Bearer {_author_token()}"},
    )

    assert resp.status_code == 404


def test_revision_stores_full_markdown_content(seeded: FlaskClient) -> None:
    """Each stored revision includes the full markdown content."""
    resp = seeded.get(
        f"/api/posts/{_TEST_SLUG}/revisions/{_SHA_OLDEST}",
        headers={"Authorization": f"Bearer {_author_token()}"},
    )

    assert resp.status_code == 200
    content = resp.json["markdown_content"]
    assert content is not None
    assert len(content) > 0


def test_diff_between_two_revisions_returns_typed_lines(
    seeded: FlaskClient,
) -> None:
    """Comparing two revisions returns a diff with typed line entries."""
    resp = seeded.get(
        f"/api/posts/{_TEST_SLUG}/revisions/{_SHA_OLDEST}/diff/{_SHA_MIDDLE}",
        headers={"Authorization": f"Bearer {_author_token()}"},
    )

    assert resp.status_code == 200
    body = resp.json
    assert "from_revision" in body
    assert "to_revision" in body
    assert "diff_lines" in body

    from_rev = body["from_revision"]
    assert from_rev["sha"] == _SHA_OLDEST
    assert "short_sha" in from_rev
    assert "timestamp" in from_rev

    assert isinstance(body["diff_lines"], list)
    for line in body["diff_lines"]:
        assert "type" in line
        assert "content" in line
        assert line["type"] in (
            "addition",
            "deletion",
            "unchanged",
            "equal",
            "context",
        )


def test_diff_between_different_content_shows_changes(
    seeded: FlaskClient,
) -> None:
    """Diffing revisions with different content reports changes."""
    resp = seeded.get(
        f"/api/posts/{_TEST_SLUG}/revisions/{_SHA_OLDEST}/diff/{_SHA_MIDDLE}",
        headers={"Authorization": f"Bearer {_author_token()}"},
    )

    assert resp.status_code == 200
    diff_lines = resp.json["diff_lines"]
    mutated_lines = [
        ln for ln in diff_lines if ln["type"] in ("addition", "deletion")
    ]
    assert len(mutated_lines) > 0


def test_diff_revision_against_itself_shows_no_changes(
    seeded: FlaskClient,
) -> None:
    """Comparing a revision against itself produces no changes."""
    resp = seeded.get(
        f"/api/posts/{_TEST_SLUG}/revisions/{_SHA_OLDEST}/diff/{_SHA_OLDEST}",
        headers={"Authorization": f"Bearer {_author_token()}"},
    )

    assert resp.status_code == 200
    diff_lines = resp.json["diff_lines"]
    mutated_lines = [
        ln for ln in diff_lines if ln["type"] in ("addition", "deletion")
    ]
    assert len(mutated_lines) == 0


def test_diff_with_unknown_sha_returns_not_found(seeded: FlaskClient) -> None:
    """A diff request referencing a non-existent SHA returns 404."""
    unknown = "0000000000000000000000000000000000000000"

    resp = seeded.get(
        f"/api/posts/{_TEST_SLUG}/revisions/{unknown}/diff/{_SHA_MIDDLE}",
        headers={"Authorization": f"Bearer {_author_token()}"},
    )

    assert resp.status_code == 404


def test_revert_adds_new_entry_to_history(seeded: FlaskClient) -> None:
    """Reverting to a prior revision adds a new record to history."""
    revert_resp = seeded.post(
        f"/api/posts/{_TEST_SLUG}/revert",
        headers={"Authorization": f"Bearer {_author_token()}"},
        json={"target_sha": _SHA_OLDEST},
    )

    assert revert_resp.status_code == 200
    assert revert_resp.json["success"] is True

    history_resp = seeded.get(
        f"/api/posts/{_TEST_SLUG}/revisions",
        headers={"Authorization": f"Bearer {_author_token()}"},
    )
    assert history_resp.json["total_count"] == 4


def test_revert_response_provides_edit_page_redirect(
    seeded: FlaskClient,
) -> None:
    """Revert response includes a redirect URL pointing to the edit page."""
    resp = seeded.post(
        f"/api/posts/{_TEST_SLUG}/revert",
        headers={"Authorization": f"Bearer {_author_token()}"},
        json={"target_sha": _SHA_OLDEST},
    )

    assert resp.status_code == 200
    body = resp.json
    assert "redirect_url" in body
    assert _TEST_SLUG in body["redirect_url"]
    assert "new_commit_sha" in body


def test_revert_new_revision_is_marked_as_revert(seeded: FlaskClient) -> None:
    """The revision record created by revert has is_revert flagged."""
    revert_resp = seeded.post(
        f"/api/posts/{_TEST_SLUG}/revert",
        headers={"Authorization": f"Bearer {_author_token()}"},
        json={"target_sha": _SHA_OLDEST},
    )

    assert revert_resp.status_code == 200
    new_sha = revert_resp.json["new_commit_sha"]

    rev_resp = seeded.get(
        f"/api/posts/{_TEST_SLUG}/revisions/{new_sha}",
        headers={"Authorization": f"Bearer {_author_token()}"},
    )
    assert rev_resp.status_code == 200
    assert rev_resp.json["is_revert"] is True


def test_revert_does_not_erase_prior_history(seeded: FlaskClient) -> None:
    """Revisions that existed before a revert remain visible afterwards."""
    seeded.post(
        f"/api/posts/{_TEST_SLUG}/revert",
        headers={"Authorization": f"Bearer {_author_token()}"},
        json={"target_sha": _SHA_OLDEST},
    )

    history_resp = seeded.get(
        f"/api/posts/{_TEST_SLUG}/revisions",
        headers={"Authorization": f"Bearer {_author_token()}"},
    )
    all_shas = {r["commit_sha"] for r in history_resp.json["revisions"]}
    assert _SHA_OLDEST in all_shas
    assert _SHA_MIDDLE in all_shas
    assert _SHA_NEWEST in all_shas


def test_revert_without_target_sha_returns_error(seeded: FlaskClient) -> None:
    """Submitting a revert request without a target SHA returns 400."""
    resp = seeded.post(
        f"/api/posts/{_TEST_SLUG}/revert",
        headers={"Authorization": f"Bearer {_author_token()}"},
        json={},
    )

    assert resp.status_code == 400
    assert "error" in resp.json


def test_unauthenticated_request_is_rejected(seeded: FlaskClient) -> None:
    """Accessing revision history without an auth token returns 401."""
    resp = seeded.get(f"/api/posts/{_TEST_SLUG}/revisions")

    assert resp.status_code == 401


def test_post_author_can_view_their_revision_history(
    seeded: FlaskClient,
) -> None:
    """The post author can retrieve the full revision history for their post."""
    resp = seeded.get(
        f"/api/posts/{_TEST_SLUG}/revisions",
        headers={"Authorization": f"Bearer {_author_token()}"},
    )

    assert resp.status_code == 200
    assert len(resp.json["revisions"]) > 0


def test_admin_can_view_any_posts_revision_history(
    seeded: FlaskClient,
) -> None:
    """An admin user can retrieve revision history for any post."""
    resp = seeded.get(
        f"/api/posts/{_TEST_SLUG}/revisions",
        headers={"Authorization": f"Bearer {_admin_token()}"},
    )

    assert resp.status_code == 200
    assert len(resp.json["revisions"]) > 0


def test_non_owner_is_denied_revision_history(seeded: FlaskClient) -> None:
    """A user who does not own the post is denied access to its history."""
    resp = seeded.get(
        f"/api/posts/{_TEST_SLUG}/revisions",
        headers={"Authorization": f"Bearer {_other_token()}"},
    )

    assert resp.status_code == 403


def test_non_owner_revert_is_rejected(seeded: FlaskClient) -> None:
    """A user who does not own the post cannot revert it."""
    resp = seeded.post(
        f"/api/posts/{_TEST_SLUG}/revert",
        headers={"Authorization": f"Bearer {_other_token()}"},
        json={"target_sha": _SHA_OLDEST},
    )

    assert resp.status_code == 403
