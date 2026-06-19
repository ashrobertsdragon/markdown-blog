"""Post aggregate for content management bounded context."""

from dataclasses import dataclass
from datetime import UTC, datetime

from backend.domain.value_objects.html_content import HtmlContent
from backend.domain.value_objects.slug import Slug


@dataclass(frozen=False)
class Post:
    """Post aggregate root representing a blog post.

    Manages post lifecycle from draft creation through publishing and
    unpublishing. Part of the Content Management bounded context.

    Attributes:
        id: Database primary key, None for unpersisted posts
        slug: URL-safe identifier for the post
        title: Post title displayed to readers
        author_id: Foreign key to User aggregate
        _html_content: Internal storage for sanitized HTML content
        published: Whether post is visible to public
        published_at: UTC timestamp when post was first published
        created_at: UTC timestamp when post was created
        updated_at: UTC timestamp when post was last modified
    """

    id: int | None
    slug: Slug
    title: str
    author_id: int
    _html_content: HtmlContent | None
    published: bool
    published_at: datetime | None
    created_at: datetime
    updated_at: datetime

    @property
    def html_content(self) -> HtmlContent | None:
        """Get HTML content value object.

        Returns:
            HtmlContent value object if set, None otherwise
        """
        return self._html_content

    @classmethod
    def create_draft(cls, slug: str, title: str, author_id: int) -> "Post":
        """Create new draft post.

        Args:
            slug: URL-safe identifier (will be validated by Slug value object)
            title: Post title (cannot be empty)
            author_id: User ID of post author (must be positive)

        Returns:
            Post: New draft post instance

        Raises:
            ValueError: If title is empty or author_id is invalid
        """
        if not title or not title.strip():
            raise ValueError("Post title cannot be empty")

        if author_id <= 0:
            raise ValueError("Post author_id must be positive")

        now = datetime.now(UTC)

        return cls(
            id=None,
            slug=Slug(slug),
            title=title,
            author_id=author_id,
            _html_content=None,
            published=False,
            published_at=None,
            created_at=now,
            updated_at=now,
        )

    def publish(self, html_content: str) -> None:
        """Publish post with rendered HTML.

        Args:
            html_content: Sanitized HTML content

        Raises:
            ValueError: If html_content is None
        """
        if html_content is None:
            raise ValueError("Post html_content cannot be None")

        now = datetime.now(UTC)

        self._html_content = HtmlContent(html_content)
        self.published = True
        self.published_at = now
        self.updated_at = now

    def unpublish(self) -> None:
        """Unpublish post (hide from public)."""
        self.published = False
        self.updated_at = datetime.now(UTC)

    def to_dict(self) -> dict[str, object]:
        """Serialize Post to dictionary for JSON responses.

        Returns:
            Dictionary with all post fields serialized for API responses.
        """
        return {
            "id": self.id,
            "slug": str(self.slug),
            "title": self.title,
            "author_id": self.author_id,
            "html_content": str(self._html_content)
            if self._html_content
            else None,
            "published": self.published,
            "published_at": self.published_at.isoformat()
            if self.published_at
            else None,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }

    def to_public_dict(self) -> dict[str, object]:
        """Serialize Post for public API responses (excludes internal fields).

        Returns:
            Dictionary with public-safe fields only (no author_id, published).
        """
        assert self.published, "to_public_dict() requires published post"
        pub_at = self.published_at or self.updated_at or self.created_at
        html_val = str(self._html_content) if self._html_content else ""
        return {
            "id": self.id,
            "slug": str(self.slug),
            "title": self.title,
            "html_content": html_val,
            "published_at": pub_at.isoformat(),
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }
