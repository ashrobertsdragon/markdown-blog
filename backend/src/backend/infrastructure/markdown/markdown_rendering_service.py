"""Markdown rendering service using markdown-it-py and Pygments."""

import logging
import re

from markdown_it import MarkdownIt
from pygments import highlight
from pygments.formatters.html import HtmlFormatter
from pygments.lexers import get_lexer_by_name, guess_lexer
from pygments.util import ClassNotFound

logger = logging.getLogger(__name__)


class MarkdownRenderingService:
    """Service for converting markdown to HTML with syntax highlighting."""

    def __init__(self) -> None:
        """Initialize markdown renderer with markdown-it-py."""
        self._md = MarkdownIt()

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
            html = self._md.render(markdown_text)
            html = self._apply_syntax_highlighting(html)
            return html
        except Exception as e:
            logger.error(f"Markdown rendering failed: {e}", exc_info=True)
            return "<p>Error rendering content</p>"

    def _apply_syntax_highlighting(self, html: str) -> str:
        """Apply Pygments syntax highlighting to code blocks.

        Args:
            html: HTML content with code blocks

        Returns:
            HTML with syntax-highlighted code blocks
        """
        import html as html_module

        pattern = r'<pre><code class="language-([^"]+)">(.*?)</code></pre>'

        def replace_code_block(match: re.Match[str]) -> str:
            language = match.group(1)
            code_escaped = match.group(2)
            code = html_module.unescape(code_escaped)

            try:
                lexer = get_lexer_by_name(language, stripall=True)
                lexer_found = True
            except ClassNotFound:
                try:
                    logger.warning(f"Unknown language fallback: {language}")
                    lexer = guess_lexer(code)
                    lexer_found = True
                except ClassNotFound:
                    logger.debug(f"No lexer found for language: {language}")
                    lexer_found = False

            if not lexer_found:
                return match.group(0)

            formatter = HtmlFormatter(nowrap=True, noclasses=False)
            highlighted = highlight(code, lexer, formatter)

            css_class = f"highlight highlight-{language}"
            result = f'<div class="{css_class}"><pre>{highlighted}</pre></div>'
            return result

        html = re.sub(pattern, replace_code_block, html, flags=re.DOTALL)

        return html
