"""Unit tests for CommentStreamService.

Covers the publish/subscribe contract for the in-process SSE fan-out
service that backs the comment stream endpoint:
- publish() broadcasts to all active subscribers for a slug
- subscribe() yields SSE-formatted event strings
- subscribe() with last_comment_id yields only comments with id > N
- pending-moderation comments are never emitted by publish()
- multiple independent slugs do not cross-contaminate
"""

import json
import threading
from collections.abc import Generator
from datetime import UTC, datetime
from typing import Any, cast

import pytest

from backend.domain.aggregates.comment import Comment
from backend.domain.value_objects.comment_text import CommentText
from backend.infrastructure.realtime.comment_stream_service import (
    CommentPayload,
)


def _to_payload(comment: Comment) -> CommentPayload:
    """Build a CommentPayload from a Comment aggregate."""
    assert comment.id is not None
    return CommentPayload(
        id=comment.id,
        post_id=comment.post_id,
        text=str(comment.text),
        parent_id=comment.parent_id,
        created_at=comment.created_at.isoformat(),
        updated_at=comment.updated_at.isoformat(),
        is_deleted=comment.is_deleted,
        is_pending_moderation=comment.is_pending_moderation,
        is_post_author=False,
    )


@pytest.fixture
def approved_comment() -> Comment:
    """Return an approved comment ready for streaming."""
    return Comment(
        id=20,
        post_id=1,
        author_id=5,
        _text=CommentText("Approved comment"),
        parent_id=None,
        created_at=datetime(2024, 6, 1, tzinfo=UTC),
        updated_at=datetime(2024, 6, 1, tzinfo=UTC),
        is_deleted=False,
        is_pending_moderation=False,
    )


@pytest.fixture
def pending_comment() -> Comment:
    """Return a comment flagged as pending moderation."""
    return Comment(
        id=21,
        post_id=1,
        author_id=6,
        _text=CommentText("Pending moderation comment"),
        parent_id=None,
        created_at=datetime(2024, 6, 1, tzinfo=UTC),
        updated_at=datetime(2024, 6, 1, tzinfo=UTC),
        is_deleted=False,
        is_pending_moderation=True,
    )


def _drain(gen: Generator[str], max_items: int = 10) -> list[str]:
    """Consume up to max_items from a generator and return them as a list."""
    results = []
    for item in gen:
        results.append(item)
        if len(results) >= max_items:
            break
    return results


def _parse_event_data(sse_line: str) -> dict[str, Any]:
    """Extract and parse the JSON payload from a single SSE data line."""
    prefix = "data: "
    assert sse_line.startswith(prefix), f"Not an SSE data line: {sse_line!r}"
    payload = sse_line[len(prefix) :].strip()
    return cast(dict[str, Any], json.loads(payload))


def test_service_publish_broadcasts_to_subscriber(
    approved_comment: Comment,
) -> None:
    """publish() delivers the comment to an active subscribe() generator.

    The fundamental contract of CommentStreamService: a subscriber that
    calls subscribe() before publish() fires must receive exactly one SSE
    event containing the comment data.
    """
    from backend.infrastructure.realtime.comment_stream_service import (
        CommentStreamService,
    )

    service = CommentStreamService()
    received: list[str] = []
    ready = threading.Event()

    def subscriber() -> None:
        """Block on the generator until one event arrives."""
        gen = service.subscribe("test-post")
        ready.set()
        for event in gen:
            received.append(event)
            break

    sub_thread = threading.Thread(target=subscriber)
    sub_thread.start()
    ready.wait(timeout=5)

    service.publish("test-post", _to_payload(approved_comment))
    sub_thread.join(timeout=5)

    assert len(received) == 1
    data = _parse_event_data(received[0])
    assert data["id"] == approved_comment.id


def test_service_publish_broadcasts_to_all_subscribers(
    approved_comment: Comment,
) -> None:
    """publish() delivers to every concurrent subscriber for the same slug.

    Multiple browser tabs may hold open streams for the same post. A single
    publish() call must fan out to all of them, not just the first.
    """
    from backend.infrastructure.realtime.comment_stream_service import (
        CommentStreamService,
    )

    service = CommentStreamService()
    received_a: list[str] = []
    received_b: list[str] = []
    ready_a = threading.Event()
    ready_b = threading.Event()

    def subscriber_a() -> None:
        """First concurrent subscriber."""
        gen = service.subscribe("test-post")
        ready_a.set()
        for event in gen:
            received_a.append(event)
            break

    def subscriber_b() -> None:
        """Second concurrent subscriber."""
        gen = service.subscribe("test-post")
        ready_b.set()
        for event in gen:
            received_b.append(event)
            break

    t_a = threading.Thread(target=subscriber_a)
    t_b = threading.Thread(target=subscriber_b)
    t_a.start()
    t_b.start()

    ready_a.wait(timeout=5)
    ready_b.wait(timeout=5)

    service.publish("test-post", _to_payload(approved_comment))

    t_a.join(timeout=5)
    t_b.join(timeout=5)

    assert len(received_a) == 1
    assert len(received_b) == 1


def test_service_publish_does_not_cross_contaminate_slugs(
    approved_comment: Comment,
) -> None:
    """publish() for one slug does not deliver to subscribers of another.

    Each post has its own independent stream. Publishing to 'post-a' must
    not trigger the generator for 'post-b', even within the same service
    instance.
    """
    from backend.infrastructure.realtime.comment_stream_service import (
        CommentStreamService,
    )

    service = CommentStreamService()
    received_b: list[str] = []
    published = threading.Event()

    def subscriber_b() -> None:
        """Subscriber listening on a different slug."""
        gen = service.subscribe("post-b")
        published.wait(timeout=3)
        received_b.extend(_drain(gen, max_items=1))

    t_b = threading.Thread(target=subscriber_b)
    t_b.start()

    service.publish("post-a", _to_payload(approved_comment))
    published.set()
    t_b.join(timeout=5)

    assert len(received_b) == 0


def test_service_subscribe_with_last_comment_id_filters_older_events(
    approved_comment: Comment,
) -> None:
    """subscribe(last_comment_id=N) skips events with id <= N.

    Reconnecting clients pass the id of the last event they received so
    the service can replay only newer comments. Events whose id is <= N
    must not appear in the generator output.
    """
    from backend.infrastructure.realtime.comment_stream_service import (
        CommentStreamService,
    )

    service = CommentStreamService()
    received: list[str] = []
    ready = threading.Event()

    assert approved_comment.id is not None
    last_seen_id = approved_comment.id

    def subscriber() -> None:
        """Subscribe with last_comment_id equal to the comment's id."""
        gen = service.subscribe("test-post", last_comment_id=last_seen_id)
        ready.set()
        received.extend(_drain(gen, max_items=1))

    t = threading.Thread(target=subscriber)
    t.start()
    ready.wait(timeout=5)

    service.publish("test-post", _to_payload(approved_comment))
    t.join(timeout=3)

    assert len(received) == 0


def test_service_subscribe_with_last_comment_id_delivers_newer_events(
    approved_comment: Comment,
) -> None:
    """subscribe(last_comment_id=N) delivers events with id > N.

    A comment whose id is strictly greater than last_comment_id must be
    forwarded to the subscriber so catch-up delivery works correctly after
    a reconnect.
    """
    from backend.infrastructure.realtime.comment_stream_service import (
        CommentStreamService,
    )

    service = CommentStreamService()
    received: list[str] = []
    ready = threading.Event()

    assert approved_comment.id is not None
    last_seen_id = approved_comment.id - 1

    def subscriber() -> None:
        """Subscribe with last_comment_id one below the comment's id."""
        gen = service.subscribe("test-post", last_comment_id=last_seen_id)
        ready.set()
        for event in gen:
            received.append(event)
            break

    t = threading.Thread(target=subscriber)
    t.start()
    ready.wait(timeout=5)

    service.publish("test-post", _to_payload(approved_comment))
    t.join(timeout=5)

    assert len(received) == 1
    data = _parse_event_data(received[0])
    assert data["id"] == approved_comment.id


def test_service_publish_excludes_pending_moderation_comments(
    pending_comment: Comment,
) -> None:
    """publish() must not broadcast pending-moderation comments.

    Comments awaiting moderation review are not yet approved for public
    display. The service must silently drop them so pending content never
    reaches live EventSource clients.
    """
    from backend.infrastructure.realtime.comment_stream_service import (
        CommentStreamService,
    )

    service = CommentStreamService()
    received: list[str] = []
    published = threading.Event()

    def subscriber() -> None:
        """Collect any events delivered after publish fires."""
        gen = service.subscribe("test-post")
        published.wait(timeout=3)
        received.extend(_drain(gen, max_items=1))

    t = threading.Thread(target=subscriber)
    t.start()

    service.publish("test-post", _to_payload(pending_comment))
    published.set()
    t.join(timeout=5)

    assert len(received) == 0


def test_service_subscribe_yields_sse_formatted_strings(
    approved_comment: Comment,
) -> None:
    """subscribe() generator output conforms to SSE wire format.

    Each yielded string must start with 'data: ' and end with the
    double-newline SSE message terminator so the browser's EventSource
    can parse it without any additional transformation.
    """
    from backend.infrastructure.realtime.comment_stream_service import (
        CommentStreamService,
    )

    service = CommentStreamService()
    received: list[str] = []
    ready = threading.Event()

    def subscriber() -> None:
        """Collect one SSE event."""
        gen = service.subscribe("test-post")
        ready.set()
        for event in gen:
            received.append(event)
            break

    t = threading.Thread(target=subscriber)
    t.start()
    ready.wait(timeout=5)

    service.publish("test-post", _to_payload(approved_comment))
    t.join(timeout=5)

    assert len(received) == 1
    event = received[0]
    assert event.startswith("data: ")
    assert event.endswith("\n\n")
