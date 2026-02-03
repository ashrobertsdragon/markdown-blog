"""CreateDraftCommand for draft post creation.

This module defines the command object for creating new draft posts.
Part of the Content Management bounded context application layer.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class CreateDraftCommand:
    """Command to create a new draft post.

    This command encapsulates the intent to create a new unpublished draft
    post. Validation is deferred to the domain layer (Post aggregate and
    Slug value object) via the handler.

    Attributes:
        slug: URL-safe identifier for the post (will be normalized)
        title: Post title to be displayed
        author_id: User ID of the post author
    """

    slug: str
    title: str
    author_id: int

    def __post_init__(self) -> None:
        """Validate input size constraints to prevent resource exhaustion.

        Size validation happens at the command layer to prevent DoS attacks
        and resource exhaustion. Domain validation (empty slug, invalid
        author_id) is deferred to the domain layer.

        Raises:
            ValueError: If slug exceeds 1000 characters
            ValueError: If title exceeds 10000 characters
        """
        if len(self.slug) > 1000:
            raise ValueError(
                f"Slug length {len(self.slug)} exceeds maximum "
                f"of 1000 characters"
            )

        if len(self.title) > 10000:
            raise ValueError(
                f"Title length {len(self.title)} exceeds maximum "
                f"of 10000 characters"
            )
