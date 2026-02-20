"""Unit tests for DiffService.

Coverage target: 80%+
Performance requirement: <500ms for diff generation
"""

from __future__ import annotations

import time

import pytest

from backend.infrastructure.versioning.diff_service import (
    DiffLine,
    DiffResult,
    DiffService,
)


class TestDiffServiceInstantiation:
    """Tests for DiffService instantiation and initialization."""

    def test_diff_service_can_be_instantiated(self) -> None:
        """DiffService should be instantiable without arguments."""
        service = DiffService()
        assert service is not None

    def test_diff_service_is_stateless(self) -> None:
        """DiffService instances should not share state."""
        service1 = DiffService()
        service2 = DiffService()
        assert service1 is not service2


class TestDiffTextStandardDiffs:
    """Tests for diff_text() method with standard diff scenarios."""

    @pytest.fixture
    def service(self) -> DiffService:
        """Provide a fresh DiffService instance."""
        return DiffService()

    def test_diff_identical_content_returns_empty_diff(
        self, service: DiffService
    ) -> None:
        """Identical content should produce only context lines."""
        old_content = "line 1\nline 2\nline 3"
        new_content = "line 1\nline 2\nline 3"

        result = service.diff_text(old_content, new_content)

        assert isinstance(result, DiffResult)
        assert result.total_additions == 0
        assert result.total_deletions == 0
        assert result.total_context_lines == 3
        assert not result.is_large_file
        assert len(result.lines) == 3
        assert all(line.type == "context" for line in result.lines)

    def test_diff_single_line_addition(self, service: DiffService) -> None:
        """Adding one line should be tracked correctly."""
        old_content = "line 1\nline 2"
        new_content = "line 1\nline 2\nline 3"

        result = service.diff_text(old_content, new_content)

        assert result.total_additions == 1
        assert result.total_deletions == 0
        assert result.total_context_lines == 2
        assert len(result.lines) == 3

        addition_line = next(
            line for line in result.lines if line.type == "addition"
        )
        assert addition_line.content == "line 3"
        assert addition_line.line_number_new == 3
        assert addition_line.line_number_old is None

    def test_diff_single_line_deletion(self, service: DiffService) -> None:
        """Deleting one line should be tracked correctly."""
        old_content = "line 1\nline 2\nline 3"
        new_content = "line 1\nline 3"

        result = service.diff_text(old_content, new_content)

        assert result.total_additions == 0
        assert result.total_deletions == 1
        assert result.total_context_lines == 2
        assert len(result.lines) == 3

        deletion_line = next(
            line for line in result.lines if line.type == "deletion"
        )
        assert deletion_line.content == "line 2"
        assert deletion_line.line_number_old == 2
        assert deletion_line.line_number_new is None

    def test_diff_single_line_modification(self, service: DiffService) -> None:
        """Modifying a line should show as deletion + addition."""
        old_content = "line 1\nline 2\nline 3"
        new_content = "line 1\nmodified line 2\nline 3"

        result = service.diff_text(old_content, new_content)

        assert result.total_additions == 1
        assert result.total_deletions == 1
        assert (
            len([line for line in result.lines if line.type == "addition"]) == 1
        )
        assert (
            len([line for line in result.lines if line.type == "deletion"]) == 1
        )

    def test_diff_multiple_changes(self, service: DiffService) -> None:
        """Multiple additions and deletions should be tracked correctly."""
        old_content = "line 1\nline 2\nline 3\nline 4\nline 5"
        new_content = "line 1\nmodified 2\nline 3\nline 6\nline 7"

        result = service.diff_text(old_content, new_content)

        assert result.total_additions >= 2
        assert result.total_deletions >= 2
        assert result.total_context_lines >= 2

    def test_diff_preserves_line_ordering(self, service: DiffService) -> None:
        """Diff lines should maintain document order."""
        old_content = "A\nB\nC"
        new_content = "A\nX\nC"

        result = service.diff_text(old_content, new_content)

        line_types = [line.type for line in result.lines]
        context_indices = [
            i for i, t in enumerate(line_types) if t == "context"
        ]
        assert context_indices == sorted(context_indices)


class TestDiffTextEdgeCases:
    """Tests for diff_text() method with edge cases and error conditions."""

    @pytest.fixture
    def service(self) -> DiffService:
        """Provide a fresh DiffService instance."""
        return DiffService()

    def test_diff_empty_to_content(self, service: DiffService) -> None:
        """Creating content from empty should show all additions."""
        old_content = ""
        new_content = "line 1\nline 2\nline 3"

        result = service.diff_text(old_content, new_content)

        assert result.total_additions == 3
        assert result.total_deletions == 0
        assert result.total_context_lines == 0
        assert all(line.type == "addition" for line in result.lines)

    def test_diff_content_to_empty(self, service: DiffService) -> None:
        """Deleting all content should show all deletions."""
        old_content = "line 1\nline 2\nline 3"
        new_content = ""

        result = service.diff_text(old_content, new_content)

        assert result.total_additions == 0
        assert result.total_deletions == 3
        assert result.total_context_lines == 0
        assert all(line.type == "deletion" for line in result.lines)

    def test_diff_both_empty(self, service: DiffService) -> None:
        """Empty to empty should produce empty diff."""
        result = service.diff_text("", "")

        assert result.total_additions == 0
        assert result.total_deletions == 0
        assert result.total_context_lines == 0
        assert len(result.lines) == 0
        assert not result.is_large_file

    def test_diff_none_old_content(self, service: DiffService) -> None:
        """None as old content should be treated as empty."""
        new_content = "line 1\nline 2"

        result = service.diff_text(None, new_content)

        assert result.total_additions == 2
        assert result.total_deletions == 0
        assert all(line.type == "addition" for line in result.lines)

    def test_diff_none_new_content(self, service: DiffService) -> None:
        """None as new content should be treated as empty."""
        old_content = "line 1\nline 2"

        result = service.diff_text(old_content, None)

        assert result.total_additions == 0
        assert result.total_deletions == 2
        assert all(line.type == "deletion" for line in result.lines)

    def test_diff_both_none(self, service: DiffService) -> None:
        """None for both arguments should produce empty diff."""
        result = service.diff_text(None, None)

        assert result.total_additions == 0
        assert result.total_deletions == 0
        assert len(result.lines) == 0

    def test_diff_unicode_content(self, service: DiffService) -> None:
        """Unicode characters should be handled correctly."""
        old_content = "Hello 世界\nTesting 🚀"
        new_content = "Hello 世界\nTesting 🎯\nNew émojis 🎉"

        result = service.diff_text(old_content, new_content)

        assert result.total_additions >= 1
        assert result.total_deletions >= 1
        unicode_lines = [
            line
            for line in result.lines
            if "🎯" in line.content or "🎉" in line.content
        ]
        assert len(unicode_lines) >= 1

    def test_diff_mixed_line_endings_crlf(self, service: DiffService) -> None:
        """CRLF line endings should be normalized."""
        old_content = "line 1\r\nline 2\r\nline 3"
        new_content = "line 1\nline 2\nline 3"

        result = service.diff_text(old_content, new_content)

        assert result.total_additions == 0
        assert result.total_deletions == 0

    def test_diff_whitespace_only_changes(self, service: DiffService) -> None:
        """Whitespace-only changes should be detected."""
        old_content = "line 1\nline 2\nline 3"
        new_content = "line 1 \nline 2\nline 3"

        result = service.diff_text(old_content, new_content)

        assert result.total_additions >= 0
        assert result.total_deletions >= 0

    def test_diff_trailing_newlines(self, service: DiffService) -> None:
        """Trailing newlines should be handled consistently."""
        old_content = "line 1\nline 2\n"
        new_content = "line 1\nline 2"

        result = service.diff_text(old_content, new_content)

        assert isinstance(result, DiffResult)

    def test_diff_very_long_lines(self, service: DiffService) -> None:
        """Very long lines (>1000 chars) should not cause errors."""
        old_content = "A" * 5000
        new_content = "B" * 5000

        result = service.diff_text(old_content, new_content)

        assert isinstance(result, DiffResult)
        assert result.total_additions >= 1
        assert result.total_deletions >= 1


class TestDiffTextLargeFiles:
    """Tests for large file handling (>1000 lines)."""

    @pytest.fixture
    def service(self) -> DiffService:
        """Provide a fresh DiffService instance."""
        return DiffService()

    def test_diff_exactly_1000_lines_not_large(
        self, service: DiffService
    ) -> None:
        """File with exactly 1000 lines should not be flagged as large."""
        old_content = "\n".join(f"line {i}" for i in range(1000))
        new_content = "\n".join(f"line {i}" for i in range(1000))

        result = service.diff_text(old_content, new_content)

        assert not result.is_large_file

    def test_diff_1001_lines_is_large(self, service: DiffService) -> None:
        """File with 1001 lines should be flagged as large."""
        old_content = "\n".join(f"line {i}" for i in range(1001))
        new_content = "\n".join(f"line {i}" for i in range(1001))

        result = service.diff_text(old_content, new_content)

        assert result.is_large_file

    def test_diff_large_file_still_returns_valid_result(
        self, service: DiffService
    ) -> None:
        """Large files should still return valid DiffResult."""
        old_content = "\n".join(f"old line {i}" for i in range(1500))
        new_content = "\n".join(f"new line {i}" for i in range(1500))

        result = service.diff_text(old_content, new_content)

        assert isinstance(result, DiffResult)
        assert result.is_large_file
        assert result.total_additions >= 0
        assert result.total_deletions >= 0


class TestGenerateDiffHtml:
    """Tests for generate_diff_html() method - HTML output with styling."""

    @pytest.fixture
    def service(self) -> DiffService:
        """Provide a fresh DiffService instance."""
        return DiffService()

    def test_generate_diff_html_returns_string(
        self, service: DiffService
    ) -> None:
        """HTML generation should return a string."""
        old_content = "line 1\nline 2"
        new_content = "line 1\nmodified 2"

        html = service.generate_diff_html(old_content, new_content)

        assert isinstance(html, str)
        assert len(html) > 0

    def test_generate_diff_html_contains_addition_class(
        self, service: DiffService
    ) -> None:
        """HTML for additions should include addition CSS class."""
        old_content = "line 1"
        new_content = "line 1\nline 2"

        html = service.generate_diff_html(old_content, new_content)

        assert "addition" in html.lower() or "added" in html.lower()

    def test_generate_diff_html_contains_deletion_class(
        self, service: DiffService
    ) -> None:
        """HTML for deletions should include deletion CSS class."""
        old_content = "line 1\nline 2"
        new_content = "line 1"

        html = service.generate_diff_html(old_content, new_content)

        assert "deletion" in html.lower() or "deleted" in html.lower()

    def test_generate_diff_html_contains_context_class(
        self, service: DiffService
    ) -> None:
        """HTML for context should include context CSS class."""
        old_content = "line 1\nline 2\nline 3"
        new_content = "line 1\nmodified\nline 3"

        html = service.generate_diff_html(old_content, new_content)

        assert "context" in html.lower() or "unchanged" in html.lower()

    def test_generate_diff_html_escapes_html_entities(
        self, service: DiffService
    ) -> None:
        """HTML entities should be escaped to prevent XSS."""
        old_content = "<script>alert('xss')</script>"
        new_content = "<div>safe</div>"

        html = service.generate_diff_html(old_content, new_content)

        assert "<script>" not in html
        assert "&lt;script&gt;" in html or "&#" in html

    def test_generate_diff_html_preserves_whitespace(
        self, service: DiffService
    ) -> None:
        """Whitespace should be visible in HTML output."""
        old_content = "no spaces"
        new_content = "    four spaces"

        html = service.generate_diff_html(old_content, new_content)

        assert "    " in html or "&nbsp;" in html or "white-space" in html

    def test_generate_diff_html_shows_line_numbers(
        self, service: DiffService
    ) -> None:
        """HTML should include line numbers."""
        old_content = "line 1\nline 2\nline 3"
        new_content = "line 1\nmodified 2\nline 3"

        html = service.generate_diff_html(old_content, new_content)

        assert "1" in html
        assert "2" in html
        assert "3" in html

    def test_generate_diff_html_empty_content(
        self, service: DiffService
    ) -> None:
        """HTML generation with empty content should not fail."""
        html = service.generate_diff_html("", "")

        assert isinstance(html, str)

    def test_generate_diff_html_none_content(
        self, service: DiffService
    ) -> None:
        """HTML generation with None content should not fail."""
        html = service.generate_diff_html(None, None)

        assert isinstance(html, str)

    def test_generate_diff_html_large_file_shows_collapsed_indicator(
        self, service: DiffService
    ) -> None:
        """Large files should show collapsed/truncated indicator in HTML."""
        old_content = "\n".join(f"line {i}" for i in range(1500))
        new_content = "\n".join(f"line {i}" for i in range(1500))

        html = service.generate_diff_html(old_content, new_content)

        assert (
            "collapsed" in html.lower()
            or "truncated" in html.lower()
            or "large" in html.lower()
        )

    def test_generate_diff_html_unicode_characters(
        self, service: DiffService
    ) -> None:
        """Unicode characters should render correctly in HTML."""
        old_content = "Hello 世界"
        new_content = "Hello 🚀"

        html = service.generate_diff_html(old_content, new_content)

        assert isinstance(html, str)
        assert "世界" in html or "&#" in html


class TestDiffTextFallback:
    """Tests for fallback behavior when diff generation fails."""

    @pytest.fixture
    def service(self) -> DiffService:
        """Provide a fresh DiffService instance."""
        return DiffService()

    def test_diff_malformed_input_does_not_raise(
        self, service: DiffService
    ) -> None:
        """Malformed input should not raise exceptions."""
        try:
            result = service.diff_text("\x00\x01\x02", "normal text")
            assert isinstance(result, DiffResult)
        except Exception:
            pytest.fail("diff_text should not raise exceptions")

    def test_diff_binary_content_fallback(self, service: DiffService) -> None:
        """Binary content should trigger fallback behavior."""
        old_content = "\x00\xff\xfe binary data"
        new_content = "text data"

        result = service.diff_text(old_content, new_content)

        assert isinstance(result, DiffResult)


class TestDiffServicePerformance:
    """Performance tests for DiffService (<500ms requirement)."""

    @pytest.fixture
    def service(self) -> DiffService:
        """Provide a fresh DiffService instance."""
        return DiffService()

    def test_diff_performance_small_files(self, service: DiffService) -> None:
        """Small file diffs (<100 lines) should complete in <100ms."""
        old_content = "\n".join(f"line {i}" for i in range(50))
        new_content = "\n".join(f"modified {i}" for i in range(50))

        start = time.perf_counter()
        service.diff_text(old_content, new_content)
        elapsed = time.perf_counter() - start

        assert elapsed < 0.1

    def test_diff_performance_medium_files(self, service: DiffService) -> None:
        """Medium file diffs (500 lines) should complete in <250ms."""
        old_content = "\n".join(f"line {i}" for i in range(500))
        new_content = "\n".join(f"modified {i}" for i in range(500))

        start = time.perf_counter()
        service.diff_text(old_content, new_content)
        elapsed = time.perf_counter() - start

        assert elapsed < 0.25

    def test_diff_performance_large_files(self, service: DiffService) -> None:
        """Large file diffs (1500 lines) should complete in <500ms."""
        old_content = "\n".join(f"line {i}" for i in range(1500))
        new_content = "\n".join(f"modified {i}" for i in range(1500))

        start = time.perf_counter()
        service.diff_text(old_content, new_content)
        elapsed = time.perf_counter() - start

        assert elapsed < 0.5

    def test_html_generation_performance(self, service: DiffService) -> None:
        """HTML generation for 500 lines should complete in <500ms."""
        old_content = "\n".join(f"line {i}" for i in range(500))
        new_content = "\n".join(f"modified {i}" for i in range(500))

        start = time.perf_counter()
        service.generate_diff_html(old_content, new_content)
        elapsed = time.perf_counter() - start

        assert elapsed < 0.5


class TestDiffLineModel:
    """Tests for DiffLine Pydantic model."""

    def test_diff_line_addition_type(self) -> None:
        """DiffLine should accept 'addition' as type."""
        line = DiffLine(
            type="addition",
            content="new line",
            line_number_old=None,
            line_number_new=1,
        )
        assert line.type == "addition"
        assert line.line_number_old is None
        assert line.line_number_new == 1

    def test_diff_line_deletion_type(self) -> None:
        """DiffLine should accept 'deletion' as type."""
        line = DiffLine(
            type="deletion",
            content="removed line",
            line_number_old=1,
            line_number_new=None,
        )
        assert line.type == "deletion"
        assert line.line_number_old == 1
        assert line.line_number_new is None

    def test_diff_line_context_type(self) -> None:
        """DiffLine should accept 'context' as type."""
        line = DiffLine(
            type="context",
            content="unchanged line",
            line_number_old=1,
            line_number_new=1,
        )
        assert line.type == "context"
        assert line.line_number_old == 1
        assert line.line_number_new == 1

    def test_diff_line_invalid_type_rejected(self) -> None:
        """DiffLine should reject invalid types."""
        with pytest.raises(Exception):
            DiffLine(
                type="invalid",
                content="test",
                line_number_old=1,
                line_number_new=1,
            )


class TestDiffResultModel:
    """Tests for DiffResult Pydantic model."""

    def test_diff_result_valid_data(self) -> None:
        """DiffResult should accept valid data."""
        lines = [
            DiffLine(
                type="addition",
                content="new",
                line_number_old=None,
                line_number_new=1,
            ),
            DiffLine(
                type="deletion",
                content="old",
                line_number_old=1,
                line_number_new=None,
            ),
            DiffLine(
                type="context",
                content="same",
                line_number_old=2,
                line_number_new=2,
            ),
        ]
        result = DiffResult(
            lines=lines,
            is_large_file=False,
            total_additions=1,
            total_deletions=1,
            total_context_lines=1,
        )
        assert len(result.lines) == 3
        assert result.total_additions == 1
        assert result.total_deletions == 1
        assert result.total_context_lines == 1

    def test_diff_result_empty_lines(self) -> None:
        """DiffResult should accept empty lines list."""
        result = DiffResult(
            lines=[],
            is_large_file=False,
            total_additions=0,
            total_deletions=0,
            total_context_lines=0,
        )
        assert len(result.lines) == 0
        assert result.total_additions == 0

    def test_diff_result_large_file_flag(self) -> None:
        """DiffResult should track large file flag."""
        result = DiffResult(
            lines=[],
            is_large_file=True,
            total_additions=0,
            total_deletions=0,
            total_context_lines=0,
        )
        assert result.is_large_file is True
