"""Slug value object for URL-safe post identifiers.

This module provides the Slug value object which ensures all post slugs
are normalized to a consistent, URL-safe format with automatic handling
of special characters, whitespace, and case conversion.
"""

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class Slug:
    """URL-safe slug value object with automatic normalization.

    Slugs are immutable value objects that represent URL-safe identifiers
    for blog posts. They automatically normalize input strings by:
    - Converting to lowercase
    - Replacing spaces with hyphens
    - Removing special characters
    - Collapsing consecutive hyphens
    - Stripping leading/trailing hyphens

    Attributes:
        value: The normalized slug string containing only lowercase letters,
               digits, and hyphens.

    Raises:
        TypeError: If raw_slug is None.
        ValueError: If the normalized slug is empty or exceeds 200 characters.

    Examples:
        >>> slug = Slug("My First Post!!")
        >>> str(slug)
        'my-first-post'

        >>> slug = Slug("Hello   World")
        >>> str(slug)
        'hello-world'

        >>> Slug("")
        Traceback (most recent call last):
        ...
        ValueError: Slug cannot be empty
    """

    value: str

    def __init__(self, raw_slug: str) -> None:
        """Create a Slug with validation and normalization.

        Args:
            raw_slug: The raw string to normalize into a slug.

        Raises:
            TypeError: If raw_slug is None.
            ValueError: If the normalized slug is empty or exceeds 200
                characters.
        """
        if raw_slug is None:
            raise TypeError("Slug cannot be None")

        normalized = self._normalize(raw_slug)

        if not normalized:
            raise ValueError("Slug cannot be empty")

        if len(normalized) > 200:
            raise ValueError("Slug cannot exceed 200 characters")

        object.__setattr__(self, "value", normalized)

    def _normalize(self, raw_slug: str) -> str:
        """Normalize a raw string into a URL-safe slug.

        Normalization pipeline:
        1. Strip leading/trailing whitespace
        2. Convert to lowercase
        3. Replace spaces with hyphens
        4. Remove all characters except a-z, 0-9, and hyphens
        5. Collapse consecutive hyphens into a single hyphen
        6. Strip leading/trailing hyphens

        Args:
            raw_slug: The raw string to normalize.

        Returns:
            The normalized slug string.
        """
        slug = raw_slug.strip()

        slug = slug.lower()

        slug = slug.replace(" ", "-")

        slug = re.sub(r"[^a-z0-9\-]", "", slug)

        slug = re.sub(r"-+", "-", slug)

        slug = slug.strip("-")

        return slug

    def __str__(self) -> str:
        """Return the normalized slug value.

        Returns:
            The normalized slug string.
        """
        return self.value
