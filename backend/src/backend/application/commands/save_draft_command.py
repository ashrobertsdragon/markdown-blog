"""SaveDraftCommand for updating draft content.

This module defines the command object for saving updates to existing
draft posts. Part of the Content Management bounded context application
layer.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class SaveDraftCommand:
    """Command to save draft content updates.

    This command encapsulates the intent to update the markdown content of an
    existing draft post. Validation is deferred to the domain layer (Post
    aggregate and Slug value object) via the handler.

    Attributes:
        slug: Draft identifier to update
        content: New markdown content
    """

    slug: str
    content: str

    def __post_init__(self) -> None:
        """Validate input size constraints to prevent resource exhaustion.

        Size validation happens at the command layer to prevent DoS attacks
        and resource exhaustion. Domain validation (slug format, empty content)
        is deferred to the domain layer.

        Raises:
            ValueError: If slug exceeds 1000 characters
            ValueError: If content exceeds 10MB (10,000,000 chars)
        """
        if len(self.slug) > 1000:
            raise ValueError(
                f"Slug length {len(self.slug)} exceeds maximum "
                f"of 1000 characters"
            )

        if len(self.content) > 10_000_000:
            raise ValueError(
                f"Content length {len(self.content)} exceeds maximum of 10MB"
            )
