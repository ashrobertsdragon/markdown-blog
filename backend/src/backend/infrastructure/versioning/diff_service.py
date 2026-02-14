"""DiffService implementation for generating text diffs.

This service generates line-based diffs using difflib.unified_diff and produces
both structured DiffResult objects and HTML representations of diffs.
"""

from __future__ import annotations

import difflib
import html
import logging
from typing import Literal

from pydantic import BaseModel

logger = logging.getLogger(__name__)


class DiffLine(BaseModel):
    """Represents a single line in a diff result."""

    type: Literal["addition", "deletion", "context"]
    content: str
    line_number_old: int | None
    line_number_new: int | None


class DiffResult(BaseModel):
    """Represents the result of a diff operation."""

    lines: list[DiffLine]
    is_large_file: bool
    total_additions: int
    total_deletions: int
    total_context_lines: int


class DiffService:
    """Service for generating text diffs between content versions.

    Uses Python's difflib for line-based comparison and produces both
    structured data models and HTML output with styling.
    """

    LARGE_FILE_THRESHOLD = 1000

    def diff_text(
        self, old_content: str | None, new_content: str | None
    ) -> DiffResult:
        """Generate a structured diff between old and new content.

        Handles None by treating as empty string, normalizes CRLF to LF,
        and never raises exceptions (returns valid fallback result on error).
        """
        try:
            old_text = self._normalize_content(old_content)
            new_text = self._normalize_content(new_content)

            old_lines = old_text.splitlines(keepends=False)
            new_lines = new_text.splitlines(keepends=False)

            max_lines = max(len(old_lines), len(new_lines))
            is_large = max_lines > self.LARGE_FILE_THRESHOLD

            diff_lines = self._generate_diff_lines(old_lines, new_lines)

            additions = sum(1 for line in diff_lines if line.type == "addition")
            deletions = sum(1 for line in diff_lines if line.type == "deletion")
            context = sum(1 for line in diff_lines if line.type == "context")

            return DiffResult(
                lines=diff_lines,
                is_large_file=is_large,
                total_additions=additions,
                total_deletions=deletions,
                total_context_lines=context,
            )

        except Exception as e:
            logger.error(f"Error generating diff: {e}", exc_info=True)
            return DiffResult(
                lines=[],
                is_large_file=False,
                total_additions=0,
                total_deletions=0,
                total_context_lines=0,
            )

    def generate_diff_html(
        self, old_content: str | None, new_content: str | None
    ) -> str:
        """Generate HTML representation of diff with CSS classes.

        Escapes HTML entities, preserves whitespace, includes line numbers,
        and indicates large files.
        """
        try:
            diff_result = self.diff_text(old_content, new_content)

            if not diff_result.lines:
                return "<div class='diff-empty'>No changes</div>"

            html_parts = ["<div class='diff-container'>"]

            if diff_result.is_large_file:
                notice = (
                    "<div class='diff-large-file-notice'>"
                    "Large file (>1000 lines)"
                    "</div>"
                )
                html_parts.append(notice)

            html_parts.append("<pre class='diff-content'>")

            for line in diff_result.lines:
                css_class = f"diff-{line.type}"
                escaped_content = html.escape(line.content)

                if line.type == "addition":
                    prefix = "+"
                    line_num = (
                        f"{line.line_number_new}"
                        if line.line_number_new
                        else ""
                    )
                elif line.type == "deletion":
                    prefix = "-"
                    line_num = (
                        f"{line.line_number_old}"
                        if line.line_number_old
                        else ""
                    )
                else:  # context
                    prefix = " "
                    line_num = (
                        f"{line.line_number_old}"
                        if line.line_number_old
                        else ""
                    )

                html_parts.append(
                    f"<div class='{css_class}'>"
                    f"<span class='line-number'>{line_num}</span>"
                    f"<span class='line-prefix'>{prefix}</span>"
                    f"<span class='line-content'>{escaped_content}</span>"
                    f"</div>"
                )

            html_parts.append("</pre>")
            html_parts.append("</div>")

            return "".join(html_parts)

        except Exception as e:
            logger.error(f"Error generating HTML diff: {e}", exc_info=True)
            return "<div class='diff-error'>Error generating diff</div>"

    def _normalize_content(self, content: str | None) -> str:
        """Normalize content for diffing.

        Converts None to empty string and normalizes CRLF to LF.
        """
        if content is None:
            return ""
        return content.replace("\r\n", "\n")

    def _generate_diff_lines(
        self, old_lines: list[str], new_lines: list[str]
    ) -> list[DiffLine]:
        """Generate list of DiffLine objects from line lists.

        Uses difflib.unified_diff to compute changes and tracks line numbers
        for both old and new content.
        """
        diff_lines: list[DiffLine] = []

        diff_iterator = difflib.unified_diff(
            old_lines, new_lines, lineterm="", n=len(old_lines) + len(new_lines)
        )

        diff_list = list(diff_iterator)

        if not diff_list:
            for idx, line_content in enumerate(old_lines, start=1):
                diff_lines.append(
                    DiffLine(
                        type="context",
                        content=line_content,
                        line_number_old=idx,
                        line_number_new=idx,
                    )
                )
            return diff_lines

        old_line_num = 0
        new_line_num = 0

        for line in diff_list:
            if (
                line.startswith("---")
                or line.startswith("+++")
                or line.startswith("@@")
            ):
                continue

            if line.startswith("-"):
                old_line_num += 1
                diff_lines.append(
                    DiffLine(
                        type="deletion",
                        content=line[1:],
                        line_number_old=old_line_num,
                        line_number_new=None,
                    )
                )
            elif line.startswith("+"):
                new_line_num += 1
                diff_lines.append(
                    DiffLine(
                        type="addition",
                        content=line[1:],
                        line_number_old=None,
                        line_number_new=new_line_num,
                    )
                )
            else:
                old_line_num += 1
                new_line_num += 1
                content = line[1:] if line.startswith(" ") else line
                diff_lines.append(
                    DiffLine(
                        type="context",
                        content=content,
                        line_number_old=old_line_num,
                        line_number_new=new_line_num,
                    )
                )

        return diff_lines
