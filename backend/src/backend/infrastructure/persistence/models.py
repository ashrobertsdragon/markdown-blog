import datetime as dt
from datetime import datetime
from uuid import UUID

from sqlalchemy import Index, UniqueConstraint
from sqlmodel import Field, SQLModel


class User(SQLModel, table=True):
    """User table model."""

    id: int | None = Field(default=None, primary_key=True)
    email: str = Field(unique=True)
    role: str = Field(default="authenticated")
    clerk_user_id: str | None = Field(default=None, unique=True, index=True)
    created_at: datetime = Field(default_factory=lambda: datetime.now(dt.UTC))


class Post(SQLModel, table=True):
    """Post table model."""

    id: int | None = Field(default=None, primary_key=True)
    slug: str = Field(unique=True, index=True)
    title: str
    html_content: str | None = Field(default=None)
    published: bool = Field(default=False, index=True)
    published_at: datetime | None = Field(default=None, index=True)
    deleted_at: datetime | None = Field(default=None, index=True)
    author_id: int | None = Field(
        default=None, foreign_key="user.id", index=True
    )
    created_at: datetime = Field(default_factory=lambda: datetime.now(dt.UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(dt.UTC))


class PostRevisionModel(SQLModel, table=True):
    """PostRevision table model."""

    __tablename__ = "post_revisions"
    __table_args__ = (
        UniqueConstraint("post_id", "commit_sha", name="uq_post_commit"),
    )

    id: UUID | None = Field(default=None, primary_key=True)
    post_id: int = Field(foreign_key="post.id", index=True)
    commit_sha: str = Field(index=True)
    author_id: int = Field(foreign_key="user.id", index=True)
    commit_message: str
    markdown_content: str
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(dt.UTC), index=True
    )
    updated_at: datetime = Field(default_factory=lambda: datetime.now(dt.UTC))
    is_revert: bool = Field(default=False)
    attempt_count: int = Field(default=0)


class NotificationModel(SQLModel, table=True):
    """Notification queue model for the notification bounded context.

    Stores pending and processed notification records that are created when
    domain events fire (e.g. comment posted, reply received). A background
    worker reads rows with status='pending' and delivers them via email.

    Attributes:
        id: Auto-incremented primary key, None before first INSERT.
        recipient_id: FK to User who should receive the notification.
        sender_id: FK to User who triggered the event.
        event_type: Discriminator string — 'comment_posted' or
            'reply_received'.
        post_id: FK to the Post the event is associated with.
        comment_id: FK to the Comment that triggered the event.
        status: Delivery state — 'pending', 'sent', or 'failed'.
        attempt_count: Number of delivery attempts made so far.
        created_at: UTC timestamp set when the row is first inserted.
        sent_at: UTC timestamp set when the notification is delivered.
        error_message: Last error string on delivery failure, else None.
    """

    __tablename__ = "notifications"
    __table_args__ = (
        UniqueConstraint(
            "comment_id",
            "event_type",
            "recipient_id",
            name="uq_notification_comment_event_recipient",
        ),
        Index("idx_notification_status_created", "status", "created_at"),
        Index(
            "idx_notification_recipient_created", "recipient_id", "created_at"
        ),
        Index("idx_notification_next_retry", "next_retry_at"),
    )

    id: int | None = Field(default=None, primary_key=True)
    recipient_id: int = Field(foreign_key="user.id", index=True)
    sender_id: int = Field(foreign_key="user.id", index=True)
    event_type: str
    post_id: int = Field(foreign_key="post.id", index=True)
    comment_id: int = Field(foreign_key="comments.id", index=True)
    status: str = Field(default="pending", index=True)
    attempt_count: int = Field(default=0)
    created_at: datetime = Field(default_factory=lambda: datetime.now(dt.UTC))
    sent_at: datetime | None = Field(default=None)
    error_message: str | None = Field(default=None)
    next_retry_at: datetime | None = Field(default=None)
    resend_email_id: str | None = Field(default=None)


class UserNotificationPreferencesModel(SQLModel, table=True):
    """User notification preferences model.

    Stores per-user opt-out flags for the three notification categories.
    Created on first access with all-enabled defaults (opt-out model).

    Attributes:
        id: Auto-incremented primary key, None before first INSERT.
        user_id: FK to User who owns these preferences, unique per user.
        notify_on_comment_replies: Whether to send reply notifications.
        notify_on_mentions: Whether to send @mention notifications.
        notify_on_new_posts: Whether to send new-post notifications.
        created_at: UTC timestamp set when the row is first inserted.
        updated_at: UTC timestamp updated on any field change.
    """

    __tablename__ = "user_notification_preferences"

    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id", unique=True, index=True)
    notify_on_comment_replies: bool = Field(default=True)
    notify_on_mentions: bool = Field(default=True)
    notify_on_new_posts: bool = Field(default=True)
    created_at: datetime = Field(default_factory=lambda: datetime.now(dt.UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(dt.UTC))


class CommentModel(SQLModel, table=True):
    """Comment table model for the discussion bounded context.

    Stores user comments on blog posts with support for flat threading via
    parent_id, soft deletion, and moderation state. All timestamps are stored
    as UTC datetimes.

    Attributes:
        id: Auto-incremented primary key, None before first INSERT.
        post_id: Foreign key referencing the Post table.
        author_id: Foreign key referencing the User table.
        parent_id: Optional self-referential FK for reply threading.
        text: Raw comment text content.
        created_at: UTC timestamp set at creation.
        updated_at: UTC timestamp updated on any state change.
        is_deleted: Soft delete flag; True hides comment from public views.
        is_pending_moderation: True when flagged for moderator review.
    """

    __tablename__ = "comments"
    id: int | None = Field(default=None, primary_key=True)
    post_id: int = Field(foreign_key="post.id", index=True)
    author_id: int = Field(foreign_key="user.id", index=True)
    parent_id: int | None = Field(
        default=None, foreign_key="comments.id", index=True
    )
    text: str
    created_at: datetime
    updated_at: datetime
    is_deleted: bool = Field(default=False, index=True)
    is_pending_moderation: bool = Field(default=False)
