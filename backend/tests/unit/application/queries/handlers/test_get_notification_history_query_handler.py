"""Unit tests for handle_get_notification_history.

Covers:
- Returns empty list when no notifications exist
- Returns list of NotificationHistoryItem with correct fields
- Pagination: fetches limit+1, returns limit items, sets has_more=True
- Sets has_more=False when fewer items than limit returned
- Enriches items with post_title from post_repo
- Enriches items with recipient_email from user_repo
"""

from unittest.mock import MagicMock

from backend.application.queries.get_notification_history_query import (
    GetNotificationHistoryQuery,
    GetNotificationHistoryResponse,
    NotificationHistoryItem,
)
from backend.application.queries.handlers.get_notification_history_handler import (  # noqa: E501
    handle_get_notification_history,
)


def _make_query(
    *,
    user_id: int = 1,
    skip: int = 0,
    limit: int = 10,
) -> GetNotificationHistoryQuery:
    """Build a valid GetNotificationHistoryQuery."""
    return GetNotificationHistoryQuery(
        user_id=user_id,
        skip=skip,
        limit=limit,
    )


def _make_notification(
    *,
    notification_id: int = 1,
    event_type: str = "reply_received",
    post_id: int = 10,
    recipient_id: int = 1,
) -> MagicMock:
    """Build a mock Notification."""
    n = MagicMock()
    n.id = notification_id
    n.event_type = event_type
    n.post_id = post_id
    n.recipient_id = recipient_id
    return n


def _make_repos(
    notifications: list[MagicMock] | None = None,
    post_title: str = "Test Post",
    recipient_email: str = "user@example.com",
) -> tuple[MagicMock, MagicMock, MagicMock]:
    """Return (notification_repo, post_repo, user_repo) mocks."""
    notification_repo = MagicMock()
    notification_repo.list_for_user.return_value = notifications or []

    post_repo = MagicMock()
    post = MagicMock()
    post.title = post_title
    post_repo.get_by_id.return_value = post

    user_repo = MagicMock()
    user = MagicMock()
    user.email = recipient_email
    user_repo.get_by_id.return_value = user

    return notification_repo, post_repo, user_repo


def test_returns_response_type() -> None:
    """Handler returns a GetNotificationHistoryResponse."""
    query = _make_query()
    notification_repo, post_repo, user_repo = _make_repos()

    result = handle_get_notification_history(
        query, notification_repo, post_repo, user_repo
    )

    assert isinstance(result, GetNotificationHistoryResponse)


def test_returns_empty_list_when_no_notifications() -> None:
    """Empty notification list produces empty items and has_more=False."""
    query = _make_query()
    notification_repo, post_repo, user_repo = _make_repos(notifications=[])

    result = handle_get_notification_history(
        query, notification_repo, post_repo, user_repo
    )

    assert result.items == []
    assert result.has_more is False


def test_returns_notification_history_items() -> None:
    """Each notification is mapped to a NotificationHistoryItem."""
    notifications = [_make_notification(notification_id=i) for i in range(1, 4)]
    query = _make_query(limit=10)
    notification_repo, post_repo, user_repo = _make_repos(
        notifications=notifications
    )

    result = handle_get_notification_history(
        query, notification_repo, post_repo, user_repo
    )

    assert len(result.items) == 3
    assert all(
        isinstance(item, NotificationHistoryItem) for item in result.items
    )


def test_has_more_true_when_extra_item_returned() -> None:
    """has_more is True when repo returns limit+1 items."""
    notifications = [_make_notification(notification_id=i) for i in range(1, 7)]
    query = _make_query(limit=5)
    notification_repo, post_repo, user_repo = _make_repos(
        notifications=notifications
    )

    result = handle_get_notification_history(
        query, notification_repo, post_repo, user_repo
    )

    assert result.has_more is True
    assert len(result.items) == 5


def test_has_more_false_when_results_under_limit() -> None:
    """has_more is False when fewer items than limit are returned."""
    notifications = [_make_notification(notification_id=i) for i in range(1, 4)]
    query = _make_query(limit=10)
    notification_repo, post_repo, user_repo = _make_repos(
        notifications=notifications
    )

    result = handle_get_notification_history(
        query, notification_repo, post_repo, user_repo
    )

    assert result.has_more is False
    assert len(result.items) == 3


def test_fetches_limit_plus_one_from_repo() -> None:
    """Repository is called with limit+1 to detect has_more."""
    query = _make_query(skip=0, limit=10)
    notification_repo, post_repo, user_repo = _make_repos()

    handle_get_notification_history(
        query, notification_repo, post_repo, user_repo
    )

    notification_repo.list_for_user.assert_called_once_with(1, skip=0, limit=11)


def test_enriches_items_with_post_title() -> None:
    """Each item carries the post_title fetched from post_repo."""
    notification = _make_notification(post_id=42)
    query = _make_query()
    notification_repo, post_repo, user_repo = _make_repos(
        notifications=[notification], post_title="My Great Post"
    )

    result = handle_get_notification_history(
        query, notification_repo, post_repo, user_repo
    )

    assert result.items[0].post_title == "My Great Post"


def test_enriches_items_with_recipient_email() -> None:
    """Each item carries the recipient_email fetched from user_repo."""
    notification = _make_notification(recipient_id=7)
    query = _make_query()
    notification_repo, post_repo, user_repo = _make_repos(
        notifications=[notification],
        recipient_email="reader@example.com",
    )

    result = handle_get_notification_history(
        query, notification_repo, post_repo, user_repo
    )

    assert result.items[0].recipient_email == "reader@example.com"


def test_item_carries_event_type() -> None:
    """NotificationHistoryItem carries the event_type from the notification."""
    notification = _make_notification(event_type="comment_posted")
    query = _make_query()
    notification_repo, post_repo, user_repo = _make_repos(
        notifications=[notification]
    )

    result = handle_get_notification_history(
        query, notification_repo, post_repo, user_repo
    )

    assert result.items[0].event_type == "comment_posted"
