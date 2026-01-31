from dataclasses import dataclass


@dataclass(frozen=True)
class PublishPostCommand:
    """Command to publish a draft post.

    Immutable command encapsulating the intent to convert a draft to published.
    Validation deferred to handler (domain and business logic validation).

    Attributes:
        slug: The draft post identifier (URL-safe slug).
    """

    slug: str

    def __post_init__(self) -> None:
        """Validate input constraints.

        Raises:
            ValueError: If slug is empty or None.
            TypeError: If slug is not a string.
        """
        if self.slug is None:
            raise ValueError("slug is required")
        if not isinstance(self.slug, str):
            raise TypeError(f"slug must be str, not {type(self.slug).__name__}")
        if not self.slug:
            raise ValueError("slug cannot be empty")
