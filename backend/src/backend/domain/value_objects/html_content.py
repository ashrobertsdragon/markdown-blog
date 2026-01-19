"""HtmlContent value object for sanitized HTML storage.

This module provides the HtmlContent value object which stores sanitized HTML
content for published blog posts. Content is preserved exactly as provided,
assuming it has already been sanitized by HtmlSanitizer.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class HtmlContent:
    """Sanitized HTML content value object.

    Wraps sanitized HTML content for published blog posts. This is an immutable
    value object that stores HTML content exactly as provided, preserving all
    HTML structure, attributes, whitespace, and unicode characters. Sanitization
    is expected to have been performed before creating this value object.

    Attributes:
        value: The sanitized HTML string.

    Raises:
        TypeError: If raw_html is None.

    Examples:
        >>> content = HtmlContent("<p>Hello world!</p>")
        >>> str(content)
        '<p>Hello world!</p>'

        >>> content = HtmlContent("")
        >>> str(content)
        ''

        >>> HtmlContent(None)
        Traceback (most recent call last):
        ...
        TypeError: HtmlContent cannot be None
    """

    value: str

    def __init__(self, raw_html: str) -> None:
        """Create HtmlContent with validation.

        Args:
            raw_html: Sanitized HTML string. Can be an empty string since
                unpublished drafts may have empty HTML. All content is
                preserved exactly as provided.

        Raises:
            TypeError: If raw_html is None.
        """
        if raw_html is None:
            raise TypeError("HtmlContent cannot be None")

        object.__setattr__(self, "value", raw_html)

    def __str__(self) -> str:
        """Return the HTML content value.

        Returns:
            The sanitized HTML string.
        """
        return self.value
