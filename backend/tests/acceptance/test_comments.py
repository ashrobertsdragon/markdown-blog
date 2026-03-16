"""Acceptance tests for Comments spec based on requirements.md.

These tests verify flat comment system, replies, moderation, rate limiting,
and spam prevention, ensuring alignment with the Acceptance Criteria in
@.spec-workflow/specs/comments/requirements.md.
"""

from typing import Any, Protocol, cast
from unittest.mock import MagicMock, patch

from flask.testing import FlaskClient

from backend.domain.aggregates.user import User
from backend.infrastructure.persistence.database import get_engine
from backend.infrastructure.persistence.models import NotificationModel

_AUTH_HEADER = {"Authorization": "Bearer test-token"}
_SPAM_TEXT = (
    "Buy now! https://spam1.example.com https://spam2.example.com "
    "https://spam3.example.com cheap deals!"
)


class _Resp(Protocol):
    """Structural type for Flask test client responses."""

    status_code: int
    json: Any
    headers: Any


def _get(client: FlaskClient, url: str, **kw: Any) -> _Resp:
    """Make a typed GET request."""
    return cast(_Resp, client.get(url, **kw))


def _post(client: FlaskClient, url: str, **kw: Any) -> _Resp:
    """Make a typed POST request."""
    return cast(_Resp, client.post(url, **kw))


def _delete(client: FlaskClient, url: str, **kw: Any) -> _Resp:
    """Make a typed DELETE request."""
    return cast(_Resp, client.delete(url, **kw))


def _put(client: FlaskClient, url: str, **kw: Any) -> _Resp:
    """Make a typed PUT request."""
    return cast(_Resp, client.put(url, **kw))


def _post_comment(client: FlaskClient, slug: str, text: str) -> _Resp:
    """POST a comment and return the typed response."""
    return _post(
        client,
        f"/api/posts/{slug}/comments",
        headers=_AUTH_HEADER,
        json={"text": text},
    )


def test_post_comment(client: FlaskClient, published_post, mock_clerk_auth):
    """Test readers can post comments on published posts.

    Acceptance Criteria:
    - Comment form appears below published post
    - Unauthenticated user sees "Sign in to comment" message
    - Authenticated reader has name/email pre-filled from auth
    - Comment text required (min 1 character, max 5000)
    - Comment stored with: post_id, author_id, text, created_at,
      parent_id (null)
    - Comment appears at bottom of comment list immediately (optimistic)
    - URLs auto-converted to <a> tags with rel="nofollow noreferrer"
    - CommentPosted event published (for notifications)
    - Rate limit exceeded shows: "Too many comments. Please wait."
    """
    slug = published_post
    text = "This is a valid comment."

    post_resp = _post_comment(client, slug, text)

    assert post_resp.status_code == 201
    data = post_resp.json
    assert data["text"] == text
    assert data["parent_id"] is None
    assert data["is_pending_moderation"] is False
    assert "post_id" in data
    assert "created_at" in data
    assert "updated_at" in data
    assert "id" in data

    list_resp = _get(client, f"/api/posts/{slug}/comments")
    assert list_resp.status_code == 200
    list_data = list_resp.json
    assert list_data["total_count"] >= 1
    comment_ids = [c["id"] for c in list_data["comments"]]
    assert data["id"] in comment_ids

    unauth_resp = _post(
        client,
        f"/api/posts/{slug}/comments",
        json={"text": "No token"},
    )
    assert unauth_resp.status_code == 401

    empty_resp = _post_comment(client, slug, "")
    assert empty_resp.status_code == 400

    missing_post_resp = _post(
        client,
        "/api/posts/does-not-exist/comments",
        headers=_AUTH_HEADER,
        json={"text": text},
    )
    assert missing_post_resp.status_code == 404


def test_reply_to_comment(client: FlaskClient, published_post, mock_clerk_auth):
    """Test readers can reply to comments.

    Acceptance Criteria:
    - "Reply" button appears below each comment
    - Clicking "Reply" shows reply form indented under comment
    - @username of parent comment author pre-filled
    - Reply text required (min 1 character, max 5000)
    - Reply stored with parent_id = original comment's ID
    - Reply appears immediately in flat list after parent comment
    - @username mentions trigger notifications (if enabled)
    - ReplyReceived event published (for notifications)
    - Deleting reply text collapses/cancels reply form
    """
    slug = published_post

    parent_resp = _post_comment(client, slug, "Parent comment.")
    assert parent_resp.status_code == 201
    parent_id = parent_resp.json["id"]

    reply_resp = _post(
        client,
        f"/api/posts/{slug}/comments/{parent_id}/reply",
        headers=_AUTH_HEADER,
        json={"text": "@author This is a reply."},
    )
    assert reply_resp.status_code == 201
    reply_data = reply_resp.json
    assert reply_data["parent_id"] == parent_id
    assert "id" in reply_data
    assert "created_at" in reply_data

    list_resp = _get(client, f"/api/posts/{slug}/comments")
    assert list_resp.status_code == 200
    comment_ids = [c["id"] for c in list_resp.json["comments"]]
    assert reply_data["id"] in comment_ids

    missing_parent_resp = _post(
        client,
        f"/api/posts/{slug}/comments/999999/reply",
        headers=_AUTH_HEADER,
        json={"text": "Reply to nothing."},
    )
    assert missing_parent_resp.status_code == 404


def test_comment_moderation(
    client: FlaskClient,
    published_post,
    mock_clerk_auth,
    reader_user: User,
    reader_jwt_payload: dict[str, object],
    admin_user: User,
    admin_jwt_payload: dict[str, object],
):
    """Test admins and authors can delete inappropriate comments.

    Acceptance Criteria:
    - Admin views post: delete button on each comment (visible to admins)
    - Author views their post: delete button on comments by other users
    - Reader views comments: delete button only on their own comments
    - Comment author clicking "Delete" shows confirmation modal
    - Deletion confirmed removes comment from database (hard delete)
    - Deleted comment immediately disappears from comment list
    - Admin deletes comment: text replaced with "[deleted by moderator]"
      (soft delete)
    - Deleting parent comment does NOT cascade delete replies
    """
    slug = published_post

    author_comment_resp = _post_comment(client, slug, "Author comment.")
    assert author_comment_resp.status_code == 201
    author_comment_id = author_comment_resp.json["id"]

    mock_reader_adapter = MagicMock()
    mock_reader_adapter.verify_token.return_value = reader_jwt_payload
    mock_reader_repo = MagicMock()
    mock_reader_repo.find_by_clerk_user_id.return_value = reader_user

    with (
        patch(
            "backend.api.middleware.auth_middleware._get_clerk_adapter",
            return_value=mock_reader_adapter,
        ),
        patch(
            "backend.api.middleware.auth_middleware._get_user_repository",
            return_value=mock_reader_repo,
        ),
    ):
        reader_comment_resp = _post_comment(
            client, slug, "Reader's own comment."
        )
        assert reader_comment_resp.status_code == 201
        reader_comment_id = reader_comment_resp.json["id"]

        forbidden_resp = _delete(
            client,
            f"/api/posts/{slug}/comments/{author_comment_id}",
            headers=_AUTH_HEADER,
        )
        assert forbidden_resp.status_code == 403

        own_delete_resp = _delete(
            client,
            f"/api/posts/{slug}/comments/{reader_comment_id}",
            headers=_AUTH_HEADER,
        )
        assert own_delete_resp.status_code == 204

    list_after_hard = _get(client, f"/api/posts/{slug}/comments")
    ids_after_hard = [c["id"] for c in list_after_hard.json["comments"]]
    assert reader_comment_id not in ids_after_hard

    mock_admin_adapter = MagicMock()
    mock_admin_adapter.verify_token.return_value = admin_jwt_payload
    mock_admin_repo = MagicMock()
    mock_admin_repo.find_by_clerk_user_id.return_value = admin_user

    with (
        patch(
            "backend.api.middleware.auth_middleware._get_clerk_adapter",
            return_value=mock_admin_adapter,
        ),
        patch(
            "backend.api.middleware.auth_middleware._get_user_repository",
            return_value=mock_admin_repo,
        ),
    ):
        admin_soft_delete_resp = _delete(
            client,
            f"/api/admin/comments/{author_comment_id}",
            headers=_AUTH_HEADER,
        )
        assert admin_soft_delete_resp.status_code == 204

        admin_list_resp = _get(
            client,
            f"/api/posts/{slug}/comments",
            headers=_AUTH_HEADER,
        )
    assert admin_list_resp.status_code == 200
    admin_visible = {c["id"]: c for c in admin_list_resp.json["comments"]}
    assert author_comment_id in admin_visible
    assert admin_visible[author_comment_id]["is_deleted"] is True

    public_list = _get(client, f"/api/posts/{slug}/comments")
    public_ids = [c["id"] for c in public_list.json["comments"]]
    assert author_comment_id not in public_ids


def test_comment_moderation_no_cascade(
    client: FlaskClient,
    published_post,
    mock_clerk_auth,
):
    """Test deleting parent comment does not cascade-delete replies.

    Acceptance Criteria:
    - Deleting parent comment does NOT cascade delete replies
    """
    slug = published_post

    parent_resp = _post_comment(client, slug, "Parent to delete.")
    assert parent_resp.status_code == 201
    parent_id = parent_resp.json["id"]

    reply_resp = _post(
        client,
        f"/api/posts/{slug}/comments/{parent_id}/reply",
        headers=_AUTH_HEADER,
        json={"text": "Reply that should survive."},
    )
    assert reply_resp.status_code == 201
    reply_id = reply_resp.json["id"]

    delete_parent_resp = _delete(
        client,
        f"/api/posts/{slug}/comments/{parent_id}",
        headers=_AUTH_HEADER,
    )
    assert delete_parent_resp.status_code == 204

    list_resp = _get(client, f"/api/posts/{slug}/comments")
    ids = [c["id"] for c in list_resp.json["comments"]]
    assert reply_id in ids
    assert parent_id not in ids


def test_rate_limiting(
    client: FlaskClient,
    published_post,
    mock_clerk_auth,
    admin_user: User,
    admin_jwt_payload: dict[str, object],
):
    """Test spam protection via rate limiting.

    Acceptance Criteria:
    - Rate limit checks: 5 comments per 1 minute per user IP
    - Exceeding rate limit rejects comment submission
    - Rejection shows: "Too many comments. Please wait X seconds."
    - Authenticated user: rate limit per user_id (not IP)
    - Anonymous user: rate limit per IP address
    - Rate limit hit includes headers: X-RateLimit-Remaining,
      X-RateLimit-Reset
    - Rate limit window expires: counter resets automatically
    - Admin user bypasses rate limiting
    """
    slug = published_post

    for i in range(5):
        resp = _post_comment(client, slug, f"Comment number {i + 1}.")
        assert resp.status_code == 201, (
            f"Expected 201 for comment {i + 1}, got {resp.status_code}"
        )

    sixth_resp = _post_comment(client, slug, "This should be rate limited.")
    assert sixth_resp.status_code == 429
    assert "X-RateLimit-Remaining" in sixth_resp.headers
    assert sixth_resp.headers["X-RateLimit-Remaining"] == "0"
    assert "X-RateLimit-Reset" in sixth_resp.headers
    body = sixth_resp.json
    assert "error" in body
    assert "wait" in body["error"].lower() or "many" in body["error"].lower()

    mock_admin_adapter = MagicMock()
    mock_admin_adapter.verify_token.return_value = admin_jwt_payload
    mock_admin_repo = MagicMock()
    mock_admin_repo.find_by_clerk_user_id.return_value = admin_user

    with (
        patch(
            "backend.api.middleware.auth_middleware._get_clerk_adapter",
            return_value=mock_admin_adapter,
        ),
        patch(
            "backend.api.middleware.auth_middleware._get_user_repository",
            return_value=mock_admin_repo,
        ),
    ):
        admin_resp = _post_comment(client, slug, "Admin bypasses rate limit.")
        assert admin_resp.status_code == 201


def test_comment_display_real_time_updates(
    client: FlaskClient,
    published_post,
    mock_clerk_auth,
    author_user: User,
):
    """Test comments appear immediately without page refresh.

    Acceptance Criteria:
    - Existing comments displayed in chronological order
    - New comment appears within 2 seconds (polling OR websocket)
    - Each comment shows: author name, timestamp (relative: "2 minutes
      ago"), text
    - Post author's comments visually distinguished (badge: "Author")
    - >50 comments: pagination OR "Load more" button
    - Pagination: newest comments loaded first (or per-user preference)
    - @username displayed as clickable mention (links to user if
      applicable)
    """
    slug = published_post

    texts = ["First comment.", "Second comment.", "Third comment."]
    for text in texts:
        resp = _post_comment(client, slug, text)
        assert resp.status_code == 201

    list_resp = _get(client, f"/api/posts/{slug}/comments")
    assert list_resp.status_code == 200
    data = list_resp.json
    assert "comments" in data
    assert "total_count" in data
    assert "has_more" in data
    assert data["total_count"] >= 3

    comments = data["comments"]
    for comment in comments:
        assert "created_at" in comment
        assert "text" in comment
        assert "id" in comment

    created_ats = [c["created_at"] for c in comments]
    assert created_ats == sorted(created_ats), (
        "Comments must be in chronological (ascending) order"
    )

    author_comments = [c for c in comments if c["is_post_author"] is True]
    assert len(author_comments) > 0, (
        "Post author's comments must be flagged with is_post_author=True"
    )

    limit_resp = _get(client, f"/api/posts/{slug}/comments?skip=0&limit=2")
    assert limit_resp.status_code == 200
    limited = limit_resp.json
    assert len(limited["comments"]) <= 2
    assert limited["total_count"] >= 3

    if limited["total_count"] > 2:
        assert limited["has_more"] is True


def test_comment_notifications(
    client: FlaskClient,
    published_post,
    mock_clerk_auth,
    reader_user: User,
    reader_jwt_payload: dict[str, object],
):
    """Test users notified when receiving comment replies.

    Acceptance Criteria:
    - Comment author receives reply: notification sent (email, per
      preference)
    - Post author receives comment: notification sent (email, per
      preference)
    - Notification triggered: Notification record created in database
    - User disables notifications: no email sent, but record exists
    - Notification sent: unsubscribe link included in email
    - User clicks unsubscribe: preference updated, future emails not sent
    """
    slug = published_post

    mock_reader_adapter = MagicMock()
    mock_reader_adapter.verify_token.return_value = reader_jwt_payload
    mock_reader_repo = MagicMock()
    mock_reader_repo.find_by_clerk_user_id.return_value = reader_user

    with (
        patch(
            "backend.api.middleware.auth_middleware._get_clerk_adapter",
            return_value=mock_reader_adapter,
        ),
        patch(
            "backend.api.middleware.auth_middleware._get_user_repository",
            return_value=mock_reader_repo,
        ),
    ):
        comment_resp = _post_comment(
            client,
            slug,
            "Reader comment to trigger notification.",
        )
        assert comment_resp.status_code == 201
        comment_id = comment_resp.json["id"]

    from sqlmodel import Session, select

    with Session(get_engine()) as session:
        statement = select(NotificationModel).where(
            NotificationModel.comment_id == comment_id
        )
        notifications = session.exec(statement).all()

    assert len(notifications) >= 1, (
        "A notification record must be created when a comment is posted"
    )
    notification = notifications[0]
    assert notification.event_type == "comment_posted"
    assert notification.status == "pending"


def test_comment_notifications_reply(
    client: FlaskClient,
    published_post,
    mock_clerk_auth,
    reader_user: User,
    reader_jwt_payload: dict[str, object],
):
    """Test notification queued when a reply is posted to a comment.

    Acceptance Criteria:
    - Comment author receives reply: notification sent (email, per preference)
    - Notification triggered: Notification record created in database
    """
    slug = published_post

    parent_resp = _post_comment(client, slug, "Parent comment by author.")
    assert parent_resp.status_code == 201
    parent_id = parent_resp.json["id"]

    mock_reader_adapter = MagicMock()
    mock_reader_adapter.verify_token.return_value = reader_jwt_payload
    mock_reader_repo = MagicMock()
    mock_reader_repo.find_by_clerk_user_id.return_value = reader_user

    with (
        patch(
            "backend.api.middleware.auth_middleware._get_clerk_adapter",
            return_value=mock_reader_adapter,
        ),
        patch(
            "backend.api.middleware.auth_middleware._get_user_repository",
            return_value=mock_reader_repo,
        ),
    ):
        reply_resp = _post(
            client,
            f"/api/posts/{slug}/comments/{parent_id}/reply",
            headers=_AUTH_HEADER,
            json={"text": "Reader replies to author."},
        )
        assert reply_resp.status_code == 201
        reply_id = reply_resp.json["id"]

    from sqlmodel import Session, select

    with Session(get_engine()) as session:
        statement = select(NotificationModel).where(
            NotificationModel.comment_id == reply_id
        )
        notifications = session.exec(statement).all()

    assert len(notifications) >= 1, (
        "A notification record must be created when a reply is posted"
    )
    notification = notifications[0]
    assert notification.event_type == "reply_received"
    assert notification.status == "pending"


def test_spam_prevention(
    client: FlaskClient,
    published_post,
    mock_clerk_auth,
    admin_user: User,
    admin_jwt_payload: dict[str, object],
):
    """Test spam checks prevent low-quality comments.

    Acceptance Criteria:
    - Basic spam checks run:
      * Comment length not excessively short (>1 char) or long (>5000)
      * Comment doesn't consist entirely of URLs (max 2 URLs per comment)
      * Comment doesn't match known spam patterns (configurable regex)
    - Comment fails spam check: queued for moderation (not published)
    - Flagged comment: admin dashboard shows in "Pending Moderation"
    - Admin approves comment: becomes visible to readers
    - Admin rejects comment: deleted without notification to author
    - Spam detected: CommentFlaggedForModeration event published
    """
    slug = published_post

    spam_resp = _post_comment(client, slug, _SPAM_TEXT)
    assert spam_resp.status_code == 201
    spam_data = spam_resp.json
    assert spam_data["is_pending_moderation"] is True
    spam_comment_id = spam_data["id"]

    public_list = _get(client, f"/api/posts/{slug}/comments")
    public_ids = [c["id"] for c in public_list.json["comments"]]
    assert spam_comment_id not in public_ids, (
        "Pending-moderation comments must not appear in public GET"
    )

    mock_admin_adapter = MagicMock()
    mock_admin_adapter.verify_token.return_value = admin_jwt_payload
    mock_admin_repo = MagicMock()
    mock_admin_repo.find_by_clerk_user_id.return_value = admin_user

    with (
        patch(
            "backend.api.middleware.auth_middleware._get_clerk_adapter",
            return_value=mock_admin_adapter,
        ),
        patch(
            "backend.api.middleware.auth_middleware._get_user_repository",
            return_value=mock_admin_repo,
        ),
    ):
        admin_list = _get(
            client,
            f"/api/posts/{slug}/comments",
            headers=_AUTH_HEADER,
        )
        admin_ids = [c["id"] for c in admin_list.json["comments"]]
        assert spam_comment_id in admin_ids, (
            "Admin must see pending-moderation comments"
        )

        approve_resp = _put(
            client,
            f"/api/admin/comments/{spam_comment_id}/approve",
            headers=_AUTH_HEADER,
        )
        assert approve_resp.status_code == 200

    after_approve = _get(client, f"/api/posts/{slug}/comments")
    after_ids = [c["id"] for c in after_approve.json["comments"]]
    assert spam_comment_id in after_ids, (
        "Approved comment must appear in public list"
    )


def test_comment_thread_tracking(
    client: FlaskClient, published_post, mock_clerk_auth
):
    """Test reply relationships are trackable.

    Acceptance Criteria:
    - Comment with parent_id: visually indented OR prefixed with "Reply
      to @username"
    - Clicking "Reply to @username" link scrolls to parent comment
    - Deleted comment: child comments (replies) remain visible with parent
      showing "[deleted comment]"
    - Comment with replies deleted: "[deleted by author]" shows but
      replies remain visible
    """
    slug = published_post

    parent_resp = _post_comment(client, slug, "Thread root comment.")
    assert parent_resp.status_code == 201
    parent = parent_resp.json
    parent_id = parent["id"]
    assert parent["parent_id"] is None

    reply_resp = _post(
        client,
        f"/api/posts/{slug}/comments/{parent_id}/reply",
        headers=_AUTH_HEADER,
        json={"text": "Reply linking to parent."},
    )
    assert reply_resp.status_code == 201
    reply = reply_resp.json
    assert reply["parent_id"] == parent_id

    list_resp = _get(client, f"/api/posts/{slug}/comments")
    assert list_resp.status_code == 200
    comments_by_id = {c["id"]: c for c in list_resp.json["comments"]}

    assert reply["id"] in comments_by_id
    assert comments_by_id[reply["id"]]["parent_id"] == parent_id


def test_comment_export_and_admin_view(
    client: FlaskClient,
    published_post,
    mock_clerk_auth,
    admin_user: User,
    admin_jwt_payload: dict[str, object],
    reader_user: User,
    reader_jwt_payload: dict[str, object],
):
    """Test admins can view and export all comments.

    Acceptance Criteria:
    - Admin accesses moderation panel: all comments listed with post
      title, author, timestamp, text, status (published/pending/deleted)
    - Admin views comment details: parent comment context shown (if reply)
    - Admin clicks post title: taken to published post view
    - Admin clicks comment author: user profile/details displayed
    - Admin selects multiple comments: bulk actions available (delete,
      approve, reject)
    - Admin exports comments: CSV export generated with post, author,
      timestamp, text, status
    """
    slug = published_post

    normal_resp = _post_comment(client, slug, "Normal visible comment.")
    assert normal_resp.status_code == 201
    normal_id = normal_resp.json["id"]

    spam_resp = _post_comment(client, slug, _SPAM_TEXT)
    assert spam_resp.status_code == 201
    spam_id = spam_resp.json["id"]
    assert spam_resp.json["is_pending_moderation"] is True

    mock_admin_adapter = MagicMock()
    mock_admin_adapter.verify_token.return_value = admin_jwt_payload
    mock_admin_repo = MagicMock()
    mock_admin_repo.find_by_clerk_user_id.return_value = admin_user

    with (
        patch(
            "backend.api.middleware.auth_middleware._get_clerk_adapter",
            return_value=mock_admin_adapter,
        ),
        patch(
            "backend.api.middleware.auth_middleware._get_user_repository",
            return_value=mock_admin_repo,
        ),
    ):
        admin_delete_resp = _delete(
            client,
            f"/api/admin/comments/{normal_id}",
            headers=_AUTH_HEADER,
        )
        assert admin_delete_resp.status_code == 204

        admin_list_resp = _get(
            client,
            f"/api/posts/{slug}/comments",
            headers=_AUTH_HEADER,
        )

    assert admin_list_resp.status_code == 200
    admin_comments = {c["id"]: c for c in admin_list_resp.json["comments"]}

    assert spam_id in admin_comments, (
        "Admin must see pending-moderation comments"
    )
    assert admin_comments[spam_id]["is_pending_moderation"] is True

    assert normal_id in admin_comments, "Admin must see soft-deleted comments"
    assert admin_comments[normal_id]["is_deleted"] is True

    public_list = _get(client, f"/api/posts/{slug}/comments")
    public_ids = [c["id"] for c in public_list.json["comments"]]
    assert normal_id not in public_ids
    assert spam_id not in public_ids


def test_comment_permissions(
    client: FlaskClient,
    published_post,
    mock_clerk_auth,
    reader_user: User,
    reader_jwt_payload: dict[str, object],
):
    """Test permission rules for comment modification.

    Acceptance Criteria:
    - Reader views published post: sees all non-deleted comments
    - Comment pending moderation: only admins and post author see it
    - User attempts to delete another user's comment: 403 Forbidden
    - Post author clicks "Delete" on comment: soft-deleted (admin
      behavior)
    - User deletes own comment: hard-deleted
    """
    slug = published_post

    author_comment_resp = _post_comment(
        client, slug, "Author's comment visible to all."
    )
    assert author_comment_resp.status_code == 201
    author_comment_id = author_comment_resp.json["id"]

    mock_reader_adapter = MagicMock()
    mock_reader_adapter.verify_token.return_value = reader_jwt_payload
    mock_reader_repo = MagicMock()
    mock_reader_repo.find_by_clerk_user_id.return_value = reader_user

    with (
        patch(
            "backend.api.middleware.auth_middleware._get_clerk_adapter",
            return_value=mock_reader_adapter,
        ),
        patch(
            "backend.api.middleware.auth_middleware._get_user_repository",
            return_value=mock_reader_repo,
        ),
    ):
        public_list = _get(client, f"/api/posts/{slug}/comments")
        assert public_list.status_code == 200
        visible_ids = [c["id"] for c in public_list.json["comments"]]
        assert author_comment_id in visible_ids

        forbidden_resp = _delete(
            client,
            f"/api/posts/{slug}/comments/{author_comment_id}",
            headers=_AUTH_HEADER,
        )
        assert forbidden_resp.status_code == 403

        reader_comment_resp = _post_comment(
            client, slug, "Reader's own comment."
        )
        assert reader_comment_resp.status_code == 201
        reader_comment_id = reader_comment_resp.json["id"]

        own_delete_resp = _delete(
            client,
            f"/api/posts/{slug}/comments/{reader_comment_id}",
            headers=_AUTH_HEADER,
        )
        assert own_delete_resp.status_code == 204

    after_delete = _get(client, f"/api/posts/{slug}/comments")
    ids_after = [c["id"] for c in after_delete.json["comments"]]
    assert reader_comment_id not in ids_after
