"""CommentText value object for comment content validation.

This module provides the CommentText value object which stores and validates
comment text content. Text must be non-empty (after stripping) and no longer
than 5000 characters. Original whitespace and formatting is preserved.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class CommentText:
    r"""Comment text content value object.

    Immutable value object that stores validated comment text. The original
    text is preserved exactly as provided, including internal whitespace,
    newlines, and unicode characters. Validation rejects None, whitespace-only
    strings, and strings exceeding 5000 characters.

    Attributes:
        value: The validated comment text string.

    Raises:
        TypeError: If raw_text is None.
        ValueError: If raw_text is empty, whitespace-only, or exceeds 5000
            chars.

    Examples:
        >>> ct = CommentText("Hello world")
        >>> str(ct)
        'Hello world'

        >>> ct = CommentText("line1\nline2")
        >>> ct.value
        'line1\nline2'

        >>> CommentText("")
        Traceback (most recent call last):
        ...
        ValueError: CommentText cannot be empty

        >>> CommentText(None)
        Traceback (most recent call last):
        ...
        TypeError: CommentText cannot be None
    """

    value: str

    def __init__(self, raw_text: str) -> None:
        """Create CommentText with validation.

        Args:
            raw_text: The comment text string. Must be non-empty after stripping
                and no longer than 5000 characters. Original text is preserved.

        Raises:
            TypeError: If raw_text is None.
            ValueError: If raw_text is empty or whitespace-only.
            ValueError: If raw_text exceeds 5000 characters.
        """
        if raw_text is None:
            raise TypeError("CommentText cannot be None")
        if not raw_text.strip():
            raise ValueError("CommentText cannot be empty")
        if len(raw_text) > 5000:
            raise ValueError(
                "CommentText exceeds maximum length of 5000 characters"
            )
        object.__setattr__(self, "value", raw_text)

    def __str__(self) -> str:
        """Return the comment text value.

        Returns:
            The original comment text string.
        """
        return self.value
