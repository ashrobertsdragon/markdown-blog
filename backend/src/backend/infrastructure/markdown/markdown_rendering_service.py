"""Markdown rendering service using markdown-it-py and Pygments."""

import logging

from markdown_it import MarkdownIt
from pygments import highlight
from pygments.formatters.html import HtmlFormatter
from pygments.lexers import TextLexer, get_lexer_by_name, guess_lexer
from pygments.util import ClassNotFound

logger = logging.getLogger(__name__)


def highlight_code(code: str, lang: str, attrs: str) -> str:
    """Highlight code using Pygments.

    Args:
        code: Source code to highlight
        lang: Language identifier
        attrs: Additional attributes (unused)

    Returns:
        HTML-formatted highlighted code wrapped in div
    """
    try:
        lexer = get_lexer_by_name(lang, stripall=True)
    except ClassNotFound:
        try:
            logger.warning(f"Unknown language, guessing: {lang}")
            lexer = guess_lexer(code)
        except ClassNotFound:
            logger.debug(f"No lexer found, using plain text: {lang}")
            lexer = TextLexer()

    formatter = HtmlFormatter(nowrap=True, noclasses=False)
    highlighted = highlight(code, lexer, formatter)

    css_class = f"highlight highlight-{lang}"
    return f'<div class="{css_class}"><pre>{highlighted}</pre></div>'


class MarkdownRenderingService:
    """Service for converting markdown to HTML with syntax highlighting."""

    def __init__(self) -> None:
        """Initialize markdown renderer with Pygments highlighting."""
        self._md = MarkdownIt(
            options_update={
                "highlight": highlight_code,
            }
        )

    def render(self, markdown_text: str) -> str:
        """Convert markdown to HTML with Pygments syntax highlighting.

        Args:
            markdown_text: Raw markdown content

        Returns:
            HTML string with syntax-highlighted code blocks

        Note:
            Returns empty string on empty input. Logs and returns error
            message on failures.
        """
        if not markdown_text or not markdown_text.strip():
            return ""

        try:
            logger.debug(f"Rendering markdown: {len(markdown_text)} chars")
            html: str = self._md.render(markdown_text)
            return html
        except Exception as e:
            logger.error(f"Markdown rendering failed: {e}", exc_info=True)
            return "<p>Error rendering content</p>"
