"""In-process SSE pub-sub service for real-time comment streaming."""

import json
import threading
from collections import deque
from collections.abc import Generator
from typing import TypedDict


class CommentPayload(TypedDict):
    """Typed structure for comment data broadcast over the SSE stream."""

    id: int
    post_id: int
    is_post_author: bool
    text: str
    parent_id: int | None
    created_at: str
    updated_at: str
    is_deleted: bool
    is_pending_moderation: bool


class CommentStreamService:
    """Thread-safe in-memory pub-sub broker for SSE comment streams.

    Each post slug has an independent set of subscriber queues. Publishing
    a comment fans out to all active subscribers for that slug. Subscribers
    block on a threading.Condition until an event arrives or a timeout fires.

    Pending-moderation comments are silently dropped before fan-out so they
    never reach public EventSource clients.
    """

    _KEEP_ALIVE_INTERVAL: int = 15
    _MAX_IDLE_SECONDS: int = 30

    def __init__(self) -> None:
        """Initialise an empty broker with no subscribers."""
        self._lock = threading.Condition(threading.Lock())
        self._queues: dict[str, list[deque[CommentPayload]]] = {}

    def publish(self, post_slug: str, comment_dict: CommentPayload) -> None:
        """Broadcast a comment to all subscribers of the given slug.

        Pending-moderation comments are dropped before delivery. Each active
        subscriber queue for the slug receives a copy of the dict.

        Args:
            post_slug: The slug identifying the post's stream channel.
            comment_dict: Serialisable comment data as returned by
                ``Comment.to_public_dict()``.
        """
        if comment_dict.get("is_pending_moderation"):
            return

        with self._lock:
            queues = self._queues.get(post_slug, [])
            for queue in queues:
                queue.append(comment_dict)
            self._lock.notify_all()

    def subscribe(
        self,
        post_slug: str,
        last_comment_id: int | None = None,
    ) -> Generator[str]:
        r"""Yield SSE-formatted strings for new comments on the given slug.

        Blocks between events using a threading.Condition. Yields a
        keep-alive line every ``_KEEP_ALIVE_INTERVAL`` seconds of inactivity
        and returns after ``_MAX_IDLE_SECONDS`` total idle time with no new
        comments.

        Args:
            post_slug: The slug identifying the post's stream channel.
            last_comment_id: When provided, comments whose ``id`` is less
                than or equal to this value are skipped (reconnect resume).

        Yields:
            SSE-formatted strings: either ``"data: {...}\n\n"`` for comment
            events or ``": keep-alive\n\n"`` for heartbeats.
        """
        queue: deque[CommentPayload] = deque()

        with self._lock:
            self._queues.setdefault(post_slug, []).append(queue)

        idle_elapsed = 0.0

        try:
            while idle_elapsed < self._MAX_IDLE_SECONDS:
                with self._lock:
                    self._lock.wait(timeout=self._KEEP_ALIVE_INTERVAL)
                    batch = list(queue)
                    queue.clear()

                if batch:
                    idle_elapsed = 0.0
                    for comment_dict in batch:
                        comment_id = comment_dict.get("id")
                        if (
                            last_comment_id is not None
                            and isinstance(comment_id, int)
                            and comment_id <= last_comment_id
                        ):
                            continue
                        yield f"data: {json.dumps(comment_dict)}\n\n"
                else:
                    idle_elapsed += self._KEEP_ALIVE_INTERVAL
                    if idle_elapsed < self._MAX_IDLE_SECONDS:
                        yield ": keep-alive\n\n"
        finally:
            with self._lock:
                slug_queues = self._queues.get(post_slug, [])
                if queue in slug_queues:
                    slug_queues.remove(queue)
                if not slug_queues:
                    self._queues.pop(post_slug, None)
