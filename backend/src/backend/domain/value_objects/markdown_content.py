"""MarkdownContent value object for raw markdown text storage.

This module provides the MarkdownContent value object which stores raw,
unprocessed markdown text for blog post drafts. Content is preserved exactly
as provided without any transformation or normalization.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class MarkdownContent:
    r"""Raw markdown content value object.

    Wraps unprocessed markdown text for blog post drafts. This is an immutable
    value object that stores markdown content exactly as provided, preserving
    all whitespace, special characters, YAML front matter, and unicode.

    Attributes:
        value: The raw markdown text string.

    Raises:
        TypeError: If raw_content is None.

    Examples:
        >>> content = MarkdownContent("# My Post\n\nHello world!")
        >>> str(content)
        '# My Post\n\nHello world!'

        >>> content = MarkdownContent("")
        >>> str(content)
        ''

        >>> MarkdownContent(None)
        Traceback (most recent call last):
        ...
        TypeError: MarkdownContent cannot be None
    """

    value: str

    def __init__(self, raw_content: str) -> None:
        """Create MarkdownContent with validation.

        Args:
            raw_content: Raw markdown text. Can be an empty string since
                drafts may be initially empty. All content is preserved
                exactly as provided.

        Raises:
            TypeError: If raw_content is None.
        """
        if raw_content is None:
            raise TypeError("MarkdownContent cannot be None")

        object.__setattr__(self, "value", raw_content)

    def __str__(self) -> str:
        """Return the raw markdown value.

        Returns:
            The raw markdown string.
        """
        return self.value
