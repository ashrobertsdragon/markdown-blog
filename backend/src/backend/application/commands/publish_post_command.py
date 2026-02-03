from dataclasses import dataclass


@dataclass(frozen=True)
class PublishPostCommand:
    """Command to publish a draft post.

    Immutable command encapsulating the intent to convert a draft to published.
    Validation deferred to handler (domain and business logic validation).

    Attributes:
        slug: The draft post identifier (URL-safe slug).
        author_id: ID of the user attempting to publish the post
        user_role: Role of the user (for admin override)
    """

    slug: str
    author_id: int
    user_role: str

    def __post_init__(self) -> None:
        """Validate input constraints.

        Raises:
            ValueError: If slug is empty or None.
            ValueError: If author_id is not positive
            ValueError: If user_role is empty
            TypeError: If slug is not a string.
        """
        if self.slug is None:
            raise ValueError("slug is required")
        if not isinstance(self.slug, str):
            raise TypeError(f"slug must be str, not {type(self.slug).__name__}")
        if not self.slug:
            raise ValueError("slug cannot be empty")
        if self.author_id <= 0:
            raise ValueError("author_id must be a positive integer")
        if not self.user_role:
            raise ValueError("user_role cannot be empty")
