import datetime as dt
from datetime import datetime

from sqlmodel import Field, SQLModel


class User(SQLModel, table=True):
    """User table model."""

    id: int | None = Field(default=None, primary_key=True)
    email: str = Field(unique=True)
    role: str = Field(default="authenticated")
    created_at: datetime = Field(default_factory=lambda: datetime.now(dt.UTC))


class Post(SQLModel, table=True):
    """Post table model."""

    id: int | None = Field(default=None, primary_key=True)
    slug: str = Field(unique=True, index=True)
    title: str
    published_html: str
    published: bool = Field(default=False)
    author_id: int | None = Field(
        default=None, foreign_key="user.id", index=True
    )
    created_at: datetime = Field(default_factory=lambda: datetime.now(dt.UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(dt.UTC))
