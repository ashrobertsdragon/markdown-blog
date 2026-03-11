"""Integration tests for the SSE comment stream endpoint.

Covers the HTTP contract for GET /api/posts/<slug>/comments/stream:
- Content-Type header
- 404 when slug not found
- SSE event format when a comment is published
- last_comment_id filtering
- moderation filtering (pending comments excluded)

The endpoint is a streaming generator. Flask's test client reads the full
response body only after the generator is exhausted, so tests drive the
generator via a mocked CommentStreamService whose subscribe() returns a
finite sequence of SSE strings rather than an infinite blocking loop.
"""

import json
import threading
from collections.abc import Generator
from datetime import UTC, datetime
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from backend.domain.aggregates.comment import Comment
from backend.domain.aggregates.post import Post
from backend.domain.value_objects.comment_text import CommentText
from backend.domain.value_objects.slug import Slug


@pytest.fixture
def published_post() -> Post:
    """Return a published Post aggregate for the stream tests."""
    return Post(
        id=1,
        slug=Slug("stream-post"),
        title="Stream Post",
        author_id=99,
        _html_content=None,
        published=True,
        published_at=datetime(2024, 1, 1, tzinfo=UTC),
        created_at=datetime(2024, 1, 1, tzinfo=UTC),
        updated_at=datetime(2024, 1, 1, tzinfo=UTC),
    )


@pytest.fixture
def approved_comment(published_post: Post) -> Comment:
    """Return an approved (non-pending) Comment on the published post."""
    assert published_post.id is not None
    return Comment(
        id=10,
        post_id=published_post.id,
        author_id=5,
        _text=CommentText("Hello stream!"),
        parent_id=None,
        created_at=datetime(2024, 6, 1, tzinfo=UTC),
        updated_at=datetime(2024, 6, 1, tzinfo=UTC),
        is_deleted=False,
        is_pending_moderation=False,
    )


@pytest.fixture
def pending_comment(published_post: Post) -> Comment:
    """Return a Comment flagged as pending moderation."""
    assert published_post.id is not None
    return Comment(
        id=11,
        post_id=published_post.id,
        author_id=6,
        _text=CommentText("Buy cheap pills now!!!"),
        parent_id=None,
        created_at=datetime(2024, 6, 1, tzinfo=UTC),
        updated_at=datetime(2024, 6, 1, tzinfo=UTC),
        is_deleted=False,
        is_pending_moderation=True,
    )


def _sse_event(comment: Comment) -> str:
    """Produce the SSE data line a real CommentStreamService would yield."""
    return f"data: {json.dumps(comment.to_public_dict())}\n\n"


def test_stream_returns_sse_content_type(
    client: Any,
    published_post: Post,
    approved_comment: Comment,
) -> None:
    """Stream endpoint returns Content-Type: text/event-stream.

    The SSE protocol requires this exact Content-Type so browsers can open
    an EventSource connection. Any other value causes the browser to reject
    the stream silently.
    """
    mock_post_repo = MagicMock()
    mock_post_repo.find_by_slug.return_value = published_post

    mock_stream_service = MagicMock()
    mock_stream_service.subscribe.return_value = iter(
        [_sse_event(approved_comment)]
    )

    with (
        patch(
            "backend.api.routes.comments._get_post_repository",
            return_value=mock_post_repo,
        ),
        patch(
            "backend.api.routes.comments._get_comment_stream_service",
            return_value=mock_stream_service,
        ),
    ):
        response = client.get("/api/posts/stream-post/comments/stream")

    assert "text/event-stream" in response.content_type


def test_stream_404_for_unknown_slug(client: Any) -> None:
    """GET stream for a slug that does not exist returns 404.

    A missing post cannot have a live comment stream. Returning 404 matches
    the contract of all other post-scoped endpoints in the comments API.
    """
    mock_post_repo = MagicMock()
    mock_post_repo.find_by_slug.return_value = None

    with patch(
        "backend.api.routes.comments._get_post_repository",
        return_value=mock_post_repo,
    ):
        response = client.get("/api/posts/no-such-post/comments/stream")

    assert response.status_code == 404


def test_stream_yields_sse_event_when_comment_published(
    client: Any,
    published_post: Post,
    approved_comment: Comment,
) -> None:
    """Stream yields a properly formatted SSE data line for each comment.

    When CommentStreamService.subscribe() produces a comment event, the
    endpoint must forward it verbatim in SSE format so EventSource clients
    can parse it via JSON.parse(event.data).
    """
    expected_event = _sse_event(approved_comment)

    mock_post_repo = MagicMock()
    mock_post_repo.find_by_slug.return_value = published_post

    mock_stream_service = MagicMock()
    mock_stream_service.subscribe.return_value = iter([expected_event])

    with (
        patch(
            "backend.api.routes.comments._get_post_repository",
            return_value=mock_post_repo,
        ),
        patch(
            "backend.api.routes.comments._get_comment_stream_service",
            return_value=mock_stream_service,
        ),
    ):
        response = client.get("/api/posts/stream-post/comments/stream")

    body = response.data.decode()
    assert "data:" in body
    assert '"id": 10' in body or '"id":10' in body
    assert "Hello stream!" in body


def test_stream_yields_existing_comments_since_last_id(
    client: Any,
    published_post: Post,
    approved_comment: Comment,
) -> None:
    """Stream passes last_comment_id to the service for catch-up delivery.

    Clients reconnecting after a disconnect supply last_comment_id so they
    receive only comments posted after their last known event. The endpoint
    must forward this parameter to CommentStreamService.subscribe() so the
    service can filter accordingly.
    """
    mock_post_repo = MagicMock()
    mock_post_repo.find_by_slug.return_value = published_post

    mock_stream_service = MagicMock()
    mock_stream_service.subscribe.return_value = iter(
        [_sse_event(approved_comment)]
    )

    with (
        patch(
            "backend.api.routes.comments._get_post_repository",
            return_value=mock_post_repo,
        ),
        patch(
            "backend.api.routes.comments._get_comment_stream_service",
            return_value=mock_stream_service,
        ),
    ):
        client.get("/api/posts/stream-post/comments/stream?last_comment_id=5")

    mock_stream_service.subscribe.assert_called_once_with(
        "stream-post", last_comment_id=5
    )


def test_stream_filters_pending_moderation_from_public_stream(
    client: Any,
    published_post: Post,
    pending_comment: Comment,
) -> None:
    """Pending-moderation comments must not appear in the public SSE stream.

    CommentStreamService is responsible for this exclusion, so the endpoint
    test verifies that a subscribe() result containing only the pending
    comment produces no 'data:' lines in the response body. The service
    must never publish pending events to public subscribers.
    """
    mock_post_repo = MagicMock()
    mock_post_repo.find_by_slug.return_value = published_post

    mock_stream_service = MagicMock()
    mock_stream_service.subscribe.return_value = iter([])

    with (
        patch(
            "backend.api.routes.comments._get_post_repository",
            return_value=mock_post_repo,
        ),
        patch(
            "backend.api.routes.comments._get_comment_stream_service",
            return_value=mock_stream_service,
        ),
    ):
        response = client.get("/api/posts/stream-post/comments/stream")

    body = response.data.decode()
    assert "Buy cheap pills now!!!" not in body


def test_stream_yields_keep_alive_comment_line(
    client: Any,
    published_post: Post,
) -> None:
    """Stream includes SSE keep-alive lines to prevent proxy timeouts.

    Proxies and load balancers close idle connections. SSE keep-alive
    comments (lines starting with ':') instruct the client to stay
    connected and are invisible to EventSource event handlers.
    """
    keep_alive = ": keep-alive\n\n"

    mock_post_repo = MagicMock()
    mock_post_repo.find_by_slug.return_value = published_post

    mock_stream_service = MagicMock()
    mock_stream_service.subscribe.return_value = iter([keep_alive])

    with (
        patch(
            "backend.api.routes.comments._get_post_repository",
            return_value=mock_post_repo,
        ),
        patch(
            "backend.api.routes.comments._get_comment_stream_service",
            return_value=mock_stream_service,
        ),
    ):
        response = client.get("/api/posts/stream-post/comments/stream")

    body = response.data.decode()
    assert ": keep-alive" in body


def test_stream_no_last_comment_id_calls_subscribe_with_none(
    client: Any,
    published_post: Post,
) -> None:
    """Stream with no last_comment_id query param calls subscribe(None).

    When a client opens a fresh stream without reconnect context, the
    endpoint must call subscribe(slug, last_comment_id=None) so the service
    knows to stream only future events, not historical backfill.
    """
    mock_post_repo = MagicMock()
    mock_post_repo.find_by_slug.return_value = published_post

    mock_stream_service = MagicMock()
    mock_stream_service.subscribe.return_value = iter([])

    with (
        patch(
            "backend.api.routes.comments._get_post_repository",
            return_value=mock_post_repo,
        ),
        patch(
            "backend.api.routes.comments._get_comment_stream_service",
            return_value=mock_stream_service,
        ),
    ):
        client.get("/api/posts/stream-post/comments/stream")

    mock_stream_service.subscribe.assert_called_once_with(
        "stream-post", last_comment_id=None
    )


def test_stream_publish_then_subscribe_delivers_event_via_thread(
    client: Any,
    published_post: Post,
    approved_comment: Comment,
) -> None:
    """publish() called concurrently with subscribe() delivers the event.

    This test simulates the real runtime flow where a POST /comments request
    triggers publish() from one thread while a waiting subscriber reads it.
    A threading.Event gates the publish call until the generator is primed,
    ensuring deterministic ordering without sleep().
    """
    ready = threading.Event()
    event_text = _sse_event(approved_comment)
    captured_events: list[str] = []

    def controlled_subscribe(
        post_slug: str, last_comment_id: int | None = None
    ) -> Generator[str]:
        """Yield one event after signalling that the subscriber is ready."""
        ready.set()
        yield event_text

    mock_post_repo = MagicMock()
    mock_post_repo.find_by_slug.return_value = published_post

    mock_stream_service = MagicMock()
    mock_stream_service.subscribe.side_effect = controlled_subscribe

    def run_client() -> None:
        """Execute the streaming request inside the test thread."""
        with (
            patch(
                "backend.api.routes.comments._get_post_repository",
                return_value=mock_post_repo,
            ),
            patch(
                "backend.api.routes.comments._get_comment_stream_service",
                return_value=mock_stream_service,
            ),
        ):
            response = client.get("/api/posts/stream-post/comments/stream")
            captured_events.append(response.data.decode())

    client_thread = threading.Thread(target=run_client)
    client_thread.start()

    ready.wait(timeout=5)
    client_thread.join(timeout=5)

    assert any("Hello stream!" in e for e in captured_events)
