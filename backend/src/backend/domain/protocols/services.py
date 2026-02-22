"""Service protocols for infrastructure layer abstractions.

These protocols define the interfaces that infrastructure services must
implement, enabling dependency injection and loose coupling between
application and infrastructure layers.
"""

from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from backend.infrastructure.versioning.diff_service import DiffResult


class MarkdownService(Protocol):
    """Protocol for markdown rendering service.

    Defines the interface for converting markdown text to HTML. Implementations
    must provide syntax highlighting and safe HTML generation.
    """

    def render(self, content: str) -> str:
        """Render markdown to HTML.

        Args:
            content: Raw markdown text

        Returns:
            Rendered HTML string
        """
        ...


class HtmlSanitizer(Protocol):
    """Protocol for HTML sanitization service.

    Defines the interface for sanitizing HTML content to prevent XSS attacks.
    Implementations must use allowlist-based filtering.
    """

    def sanitize(self, content: str) -> str:
        """Sanitize HTML content.

        Args:
            content: Raw HTML string

        Returns:
            Sanitized HTML string with dangerous elements removed
        """
        ...


class DiffService(Protocol):
    """Protocol for diff generation service.

    Defines the interface for comparing text content and generating
    line-by-line diffs.
    """

    def diff_text(
        self, old_content: str | None, new_content: str | None
    ) -> "DiffResult":
        """Generate diff between two text contents.

        Args:
            old_content: Original text content (may be None)
            new_content: New text content (may be None)

        Returns:
            DiffResult object containing lines and metadata
        """
        ...
