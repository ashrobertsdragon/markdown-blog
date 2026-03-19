"""ProcessNotificationsCommand for batch notification delivery.

This module defines the command object for processing pending notifications
in a background batch job. Part of the Notification bounded context.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class ProcessNotificationsCommand:
    """Command to process pending notifications in a batch.

    Controls how many notifications are processed per run and how many
    delivery retries are permitted before a notification is marked failed.

    Attributes:
        batch_limit: Maximum number of pending notifications to process per
            run. Must be greater than zero. Defaults to 100.
        max_retries: Maximum delivery attempts before marking a notification
            as permanently failed. Zero means no retries. Defaults to 3.
    """

    batch_limit: int = 100
    max_retries: int = 3

    def __post_init__(self) -> None:
        """Validate command parameters.

        Raises:
            ValueError: If batch_limit is not greater than zero.
            ValueError: If max_retries is negative.
        """
        if self.batch_limit <= 0:
            raise ValueError("batch_limit must be greater than 0")

        if self.batch_limit > 1000:
            raise ValueError("batch_limit cannot exceed 1000")

        if self.max_retries < 0:
            raise ValueError("max_retries must be 0 or greater")
