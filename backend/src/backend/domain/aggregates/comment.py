"""Comment aggregate for discussion bounded context."""

from dataclasses import dataclass
from datetime import UTC, datetime

from backend.domain.value_objects.comment_text import CommentText


@dataclass(frozen=False)
class Comment:
    """Comment aggregate root for the discussion bounded context.

    Represents a user comment on a blog post. Supports flat threading via
    parent_id and soft deletion for moderation. Text is stored as a
    CommentText value object to enforce content invariants.

    Attributes:
        id: Database primary key, None before persistence.
        post_id: Foreign key referencing the Post aggregate.
        author_id: Foreign key referencing the User aggregate.
        _text: CommentText value object holding validated content.
        parent_id: Foreign key to parent Comment for replies, None for roots.
        created_at: UTC timestamp set at creation, immutable.
        updated_at: UTC timestamp updated on state changes.
        is_deleted: Soft delete flag; True hides from public views.
    """

    id: int | None
    post_id: int
    author_id: int
    _text: CommentText
    parent_id: int | None
    created_at: datetime
    updated_at: datetime
    is_deleted: bool
    is_pending_moderation: bool

    def __post_init__(self) -> None:
        """Enforce runtime type contract for value object fields.

        Dataclass field annotations are not enforced at runtime. This guard
        ensures _text is always a CommentText instance so the domain contract
        holds regardless of how the aggregate is constructed.

        Raises:
            TypeError: If _text is not a CommentText instance.
        """
        if not isinstance(self._text, CommentText):
            raise TypeError("_text must be a CommentText instance")

    def __setattr__(self, name: str, value: object) -> None:
        """Prevent modification of created_at field after initialization."""
        if name == "created_at" and hasattr(self, "created_at"):
            raise AttributeError(
                "Cannot modify created_at timestamp - audit trail integrity"
            )
        object.__setattr__(self, name, value)

    @property
    def text(self) -> CommentText:
        """Return the CommentText value object.

        Returns:
            The CommentText instance holding the validated comment content.
        """
        return self._text

    @classmethod
    def create(
        cls,
        post_id: int,
        author_id: int,
        text: str,
        parent_id: int | None = None,
    ) -> "Comment":
        """Create a new Comment aggregate.

        Factory method that validates all inputs and wraps text in a
        CommentText value object before constructing the aggregate.

        Args:
            post_id: Positive integer referencing the target Post.
            author_id: Positive integer referencing the commenting User.
            text: Raw comment text; passed to CommentText for validation.
            parent_id: Optional positive integer referencing a parent Comment.

        Returns:
            New Comment instance with id=None, ready for persistence.

        Raises:
            ValueError: If post_id is not positive.
            ValueError: If author_id is not positive.
            ValueError: If parent_id is provided but not positive.
            ValueError: If text is empty, whitespace-only, or exceeds
                5000 chars.
            TypeError: If text is None.
        """
        if post_id <= 0:
            raise ValueError("post_id must be positive")
        if author_id <= 0:
            raise ValueError("author_id must be positive")
        if parent_id is not None and parent_id <= 0:
            raise ValueError("parent_id must be positive")

        comment_text = CommentText(text)
        now = datetime.now(UTC)

        return cls(
            id=None,
            post_id=post_id,
            author_id=author_id,
            _text=comment_text,
            parent_id=parent_id,
            created_at=now,
            updated_at=now,
            is_deleted=False,
            is_pending_moderation=False,
        )

    def approve(self) -> None:
        """Clear the pending moderation flag, making the comment visible.

        Sets is_pending_moderation to False and updates updated_at. Called
        by the moderation handler when an admin approves a flagged comment.
        """
        self.is_pending_moderation = False
        self.updated_at = datetime.now(UTC)

    def mark_as_pending_moderation(self) -> None:
        """Flag this comment for moderator review.

        Sets is_pending_moderation to True and updates updated_at. Called
        when the spam score meets or exceeds the moderation threshold.
        """
        self.is_pending_moderation = True
        self.updated_at = datetime.now(UTC)

    def mark_as_deleted(self) -> None:
        """Soft-delete this comment.

        Sets is_deleted to True and updates updated_at to the current UTC
        time. The comment text is preserved for moderation and thread
        integrity purposes.
        """
        self.is_deleted = True
        self.updated_at = datetime.now(UTC)

    def is_reply(self) -> bool:
        """Return True if this comment is a reply to another comment.

        Returns:
            True when parent_id is set, False for top-level comments.
        """
        return self.parent_id is not None

    def to_dict(self) -> dict[str, object]:
        """Serialize the Comment to a JSON-serializable dictionary.

        Converts domain types to primitives: CommentText to str, datetimes
        to ISO 8601 strings. All fields are always present so API clients
        can rely on a stable schema.

        Returns:
            Dictionary containing all Comment fields as serializable values.
        """
        return {
            "id": self.id,
            "post_id": self.post_id,
            "author_id": self.author_id,
            "text": str(self._text),
            "parent_id": self.parent_id,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "is_deleted": self.is_deleted,
            "is_pending_moderation": self.is_pending_moderation,
        }

    def to_public_dict(self) -> dict[str, object]:
        """Serialize the Comment for public API responses.

        Identical to to_dict() but omits author_id to avoid leaking internal
        user identifiers in public endpoints. Callers that need to compute
        author-based flags (e.g. is_post_author) should read self.author_id
        directly before calling this method.

        Returns:
            Dictionary with all Comment fields except author_id.
        """
        return {
            "id": self.id,
            "post_id": self.post_id,
            "text": str(self._text),
            "parent_id": self.parent_id,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "is_deleted": self.is_deleted,
            "is_pending_moderation": self.is_pending_moderation,
        }
