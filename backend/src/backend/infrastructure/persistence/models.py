import datetime as dt
from datetime import datetime
from uuid import UUID

from sqlalchemy import UniqueConstraint
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
    html_content: str
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
