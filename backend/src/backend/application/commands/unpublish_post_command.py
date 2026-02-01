from dataclasses import dataclass


@dataclass(frozen=True)
class UnpublishPostCommand:
    """Command to unpublish a published post.

    Immutable command encapsulating the intent to convert a published post back
    to draft status. Validation deferred to handler (domain and business logic).

    Attributes:
        slug: The post identifier (URL-safe slug).
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
