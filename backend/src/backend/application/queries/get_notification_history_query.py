"""GetNotificationHistoryQuery and response types for notification history.

This module defines the query object, item DTO, and response type for
retrieving a paginated notification history for a user. Part of the
Notification bounded context application layer.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class GetNotificationHistoryQuery:
    """Query to retrieve paginated notification history for a user.

    Attributes:
        user_id: Positive integer referencing the recipient User.
        skip: Number of notifications to skip for pagination. Defaults to 0.
        limit: Maximum number of notifications to return, 1-100. Defaults
            to 50.
    """

    user_id: int
    skip: int = 0
    limit: int = 50

    def __post_init__(self) -> None:
        """Validate query parameters.

        Raises:
            ValueError: If user_id is not greater than zero.
            ValueError: If skip is negative.
            ValueError: If limit is not between 1 and 100.
        """
        if self.user_id <= 0:
            raise ValueError("user_id must be greater than 0")

        if self.skip < 0:
            raise ValueError("skip must be 0 or greater")

        if not 1 <= self.limit <= 100:
            raise ValueError("limit must be between 1 and 100")


@dataclass(frozen=True)
class NotificationHistoryItem:
    """Single notification record for display in a user's history.

    Attributes:
        id: Database primary key of the notification.
        recipient_email: Email address of the notification recipient.
        event_type: Domain event that triggered the notification.
        post_title: Title of the post the notification relates to.
        status: Current delivery status string.
        created_at: ISO 8601 string of when the notification was created.
        sent_at: ISO 8601 string of delivery time, or None if not yet sent.
        error_message: Last delivery error description, or None.
        resend_email_id: Resend API email ID on successful delivery, or None.
    """

    id: int
    recipient_email: str
    event_type: str
    post_title: str
    status: str
    created_at: str
    sent_at: str | None
    error_message: str | None
    resend_email_id: str | None


@dataclass(frozen=True)
class GetNotificationHistoryResponse:
    """Paginated response for GetNotificationHistoryQuery.

    Attributes:
        items: Notification history items for the current page.
        has_more: True when additional items exist beyond this page.
    """

    items: list[NotificationHistoryItem]
    has_more: bool
