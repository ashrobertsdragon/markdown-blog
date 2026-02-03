from dataclasses import dataclass


@dataclass(frozen=True)
class DeleteDraftCommand:
    """Command to delete a draft post.

    Immutable command encapsulating the intent to permanently delete
    a draft from the filesystem and GitHub. Published posts cannot be
    deleted and must be unpublished first.

    Attributes:
        slug: The draft post identifier (URL-safe slug).
        author_id: ID of the user attempting to delete the draft
        user_role: Role of the user (for admin override)
    """

    slug: str
    author_id: int
    user_role: str

    def __post_init__(self) -> None:
        """Validate command parameters.

        Raises:
            ValueError: If slug is None, empty, or exceeds 1000 chars
            ValueError: If author_id is not positive
            ValueError: If user_role is empty
            TypeError: If slug is not a string
        """
        if self.slug is None:
            raise ValueError("slug is required")
        if not isinstance(self.slug, str):
            raise TypeError(f"slug must be str, not {type(self.slug).__name__}")
        if not self.slug:
            raise ValueError("slug cannot be empty")
        if len(self.slug) > 1000:
            raise ValueError(
                f"slug too long: {len(self.slug)} chars (max 1000)"
            )
        if self.author_id <= 0:
            raise ValueError("author_id must be a positive integer")
        if not self.user_role:
            raise ValueError("user_role cannot be empty")
