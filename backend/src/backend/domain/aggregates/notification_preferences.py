"""NotificationPreferences aggregate for the notification bounded context."""

from dataclasses import dataclass


@dataclass
class NotificationPreferences:
    """Notification preferences aggregate for a user.

    Represents the user's opt-out choices for email notifications.
    Defaults to all-enabled (opt-out model).

    Attributes:
        user_id: FK referencing the User who owns these preferences.
        notify_on_comment_replies: Whether to notify on comment replies.
        notify_on_mentions: Whether to notify on @mentions.
        notify_on_new_posts: Whether to notify on new posts.
    """

    user_id: int
    notify_on_comment_replies: bool
    notify_on_mentions: bool
    notify_on_new_posts: bool

    @classmethod
    def create_defaults(cls, user_id: int) -> "NotificationPreferences":
        """Create default preferences with all notifications enabled.

        Args:
            user_id: Positive integer referencing the User.

        Returns:
            NotificationPreferences with all flags set to True.

        Raises:
            ValueError: If user_id is not a positive integer.
        """
        if user_id <= 0:
            raise ValueError("user_id must be positive")
        return cls(
            user_id=user_id,
            notify_on_comment_replies=True,
            notify_on_mentions=True,
            notify_on_new_posts=True,
        )

    def should_notify_reply(self) -> bool:
        """Return whether user wants reply notifications."""
        return self.notify_on_comment_replies

    def should_notify_mention(self) -> bool:
        """Return whether user wants mention notifications."""
        return self.notify_on_mentions

    def should_notify_post(self) -> bool:
        """Return whether user wants new post notifications."""
        return self.notify_on_new_posts
