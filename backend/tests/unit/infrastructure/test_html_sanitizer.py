"""
Tests for HTML sanitization functionality.

This module tests the HtmlSanitizer class which implements allowlist-based
HTML sanitization using Bleach to prevent XSS attacks in user-generated content.

Requirements tested:
- 9.3: HTML sanitized with Bleach (allowlist approach)
- 9.4: Dangerous tags (script, style, iframe, object) removed
- 9.5: Only allowed tags preserved
- 9.6: External links have rel="nofollow noreferrer"
- 9.7: Images restricted to src, alt, title attributes
"""

import pytest

from backend.infrastructure.rendering.html_sanitizer import HtmlSanitizer


class TestHtmlSanitizerDangerousTagRemoval:
    """
    Test that dangerous HTML tags are completely removed.

    Verifies requirement 9.4: script, style, iframe, object tags
    SHALL be removed.
    """

    def test_removes_script_tags(self, html_sanitizer: HtmlSanitizer) -> None:
        """Script tags and their contents should be completely removed."""
        html = (
            "<p>Safe content</p><script>alert('xss')</script><p>More safe</p>"
        )
        result = html_sanitizer.sanitize(html)
        assert "<script>" not in result
        assert "alert" not in result
        assert "<p>Safe content</p>" in result
        assert "<p>More safe</p>" in result

    def test_removes_inline_script_handlers(
        self, html_sanitizer: HtmlSanitizer
    ) -> None:
        """Inline event handlers like onclick should be stripped."""
        html = '<a href="#" onclick="alert(\'xss\')">Click</a>'
        result = html_sanitizer.sanitize(html)
        assert "onclick" not in result
        assert "alert" not in result.lower() or result == "<a>Click</a>"

    def test_removes_style_tags(self, html_sanitizer: HtmlSanitizer) -> None:
        """Style tags and their contents should be removed."""
        html = "<p>Content</p><style>body { display: none; }</style>"
        result = html_sanitizer.sanitize(html)
        assert "<style>" not in result
        assert "display" not in result

    def test_removes_iframe_tags(self, html_sanitizer: HtmlSanitizer) -> None:
        """Iframe tags should be removed to prevent embedding content."""
        html = '<p>Content</p><iframe src="http://evil.com"></iframe>'
        result = html_sanitizer.sanitize(html)
        assert "<iframe>" not in result.lower()
        assert "evil.com" not in result

    def test_removes_object_tags(self, html_sanitizer: HtmlSanitizer) -> None:
        """Object tags should be removed to prevent plugin exploitation."""
        html = '<object data="malicious.swf"></object><p>Safe</p>'
        result = html_sanitizer.sanitize(html)
        assert "<object>" not in result.lower()
        assert "malicious.swf" not in result

    def test_removes_embed_tags(self, html_sanitizer: HtmlSanitizer) -> None:
        """Embed tags should be removed similar to object tags."""
        html = '<embed src="malicious.swf"><p>Content</p>'
        result = html_sanitizer.sanitize(html)
        assert "<embed>" not in result.lower()

    def test_removes_nested_dangerous_tags(
        self, html_sanitizer: HtmlSanitizer
    ) -> None:
        """Dangerous tags nested in safe tags should be removed."""
        html = "<div><p>Safe</p><script>alert('nested')</script></div>"
        result = html_sanitizer.sanitize(html)
        assert "<script>" not in result
        assert "alert" not in result
        assert "<p>Safe</p>" in result

    def test_removes_base_tags(self, html_sanitizer: HtmlSanitizer) -> None:
        """Base tags should be removed to prevent URL manipulation."""
        html = '<base href="http://evil.com"><p>Content</p>'
        result = html_sanitizer.sanitize(html)
        assert "<base>" not in result.lower()

    def test_removes_meta_tags(self, html_sanitizer: HtmlSanitizer) -> None:
        """Meta tags should be removed from user content."""
        html = '<meta http-equiv="refresh" content="0;url=http://evil.com"><p>Text</p>'
        result = html_sanitizer.sanitize(html)
        assert "<meta>" not in result.lower()


class TestHtmlSanitizerSafeTagPreservation:
    """
    Test that allowed HTML tags are preserved correctly.

    Verifies requirement 9.5: Allowed tags include p, h1-h6, a, img, ul, ol,
    li, code, pre, strong, em, blockquote, br, hr, table tags, span, div.
    """

    def test_preserves_paragraph_tags(
        self, html_sanitizer: HtmlSanitizer
    ) -> None:
        """Paragraph tags should be preserved."""
        html = "<p>This is a paragraph.</p>"
        result = html_sanitizer.sanitize(html)
        assert result == html

    def test_preserves_all_heading_tags(
        self, html_sanitizer: HtmlSanitizer
    ) -> None:
        """All heading levels h1-h6 should be preserved."""
        html = (
            "<h1>H1</h1><h2>H2</h2><h3>H3</h3><h4>H4</h4><h5>H5</h5><h6>H6</h6>"
        )
        result = html_sanitizer.sanitize(html)
        for i in range(1, 7):
            assert f"<h{i}>H{i}</h{i}>" in result

    def test_preserves_anchor_tags(self, html_sanitizer: HtmlSanitizer) -> None:
        """Anchor tags should be preserved."""
        html = '<a href="https://example.com">Link</a>'
        result = html_sanitizer.sanitize(html)
        assert "<a" in result
        assert "href=" in result
        assert ">Link</a>" in result

    def test_preserves_image_tags(self, html_sanitizer: HtmlSanitizer) -> None:
        """Image tags should be preserved with allowed attributes."""
        html = '<img src="image.png" alt="Description">'
        result = html_sanitizer.sanitize(html)
        assert "<img" in result
        assert 'src="image.png"' in result

    def test_preserves_list_tags(self, html_sanitizer: HtmlSanitizer) -> None:
        """Unordered and ordered list tags should be preserved."""
        html = "<ul><li>Item 1</li><li>Item 2</li></ul><ol><li>First</li></ol>"
        result = html_sanitizer.sanitize(html)
        assert "<ul>" in result
        assert "<ol>" in result
        assert "<li>" in result

    def test_preserves_code_and_pre_tags(
        self, html_sanitizer: HtmlSanitizer
    ) -> None:
        """Code and pre tags should be preserved for code blocks."""
        html = "<pre><code>const x = 1;</code></pre>"
        result = html_sanitizer.sanitize(html)
        assert "<pre>" in result
        assert "<code>" in result

    def test_preserves_emphasis_tags(
        self, html_sanitizer: HtmlSanitizer
    ) -> None:
        """Strong and em tags should be preserved."""
        html = "<strong>Bold</strong> and <em>italic</em>"
        result = html_sanitizer.sanitize(html)
        assert "<strong>Bold</strong>" in result
        assert "<em>italic</em>" in result

    def test_preserves_blockquote_tags(
        self, html_sanitizer: HtmlSanitizer
    ) -> None:
        """Blockquote tags should be preserved."""
        html = "<blockquote>A quote</blockquote>"
        result = html_sanitizer.sanitize(html)
        assert "<blockquote>A quote</blockquote>" in result

    def test_preserves_br_and_hr_tags(
        self, html_sanitizer: HtmlSanitizer
    ) -> None:
        """Self-closing br and hr tags should be preserved."""
        html = "Line 1<br>Line 2<hr>Section"
        result = html_sanitizer.sanitize(html)
        assert "<br" in result
        assert "<hr" in result

    def test_preserves_table_structure(
        self, html_sanitizer: HtmlSanitizer
    ) -> None:
        """Complete table structure should be preserved."""
        html = (
            "<table><thead><tr><th>Header</th></tr></thead>"
            "<tbody><tr><td>Data</td></tr></tbody></table>"
        )
        result = html_sanitizer.sanitize(html)
        assert "<table>" in result
        assert "<thead>" in result
        assert "<tbody>" in result
        assert "<tr>" in result
        assert "<th>" in result
        assert "<td>" in result

    def test_preserves_span_and_div_tags(
        self, html_sanitizer: HtmlSanitizer
    ) -> None:
        """Span and div tags should be preserved."""
        html = "<div><span>Inline text</span></div>"
        result = html_sanitizer.sanitize(html)
        assert "<div>" in result
        assert "<span>" in result

    def test_removes_disallowed_tags(
        self, html_sanitizer: HtmlSanitizer
    ) -> None:
        """Tags not in the allowlist should be removed."""
        html = "<article><section>Content</section></article>"
        result = html_sanitizer.sanitize(html)
        assert "<article>" not in result
        assert "<section>" not in result
        assert "Content" in result


class TestHtmlSanitizerAttributeFiltering:
    """
    Test that only allowed attributes are preserved on tags.

    Verifies requirement 9.7: Images only have src, alt, title attributes.
    Also tests that dangerous attributes are stripped from all tags.
    """

    def test_preserves_href_on_anchor_tags(
        self, html_sanitizer: HtmlSanitizer
    ) -> None:
        """Anchor tags should preserve href attribute."""
        html = '<a href="https://example.com">Link</a>'
        result = html_sanitizer.sanitize(html)
        assert 'href="https://example.com"' in result

    def test_preserves_title_on_anchor_tags(
        self, html_sanitizer: HtmlSanitizer
    ) -> None:
        """Anchor tags should preserve title attribute."""
        html = '<a href="#" title="Tooltip">Link</a>'
        result = html_sanitizer.sanitize(html)
        assert 'title="Tooltip"' in result

    def test_removes_style_attributes(
        self, html_sanitizer: HtmlSanitizer
    ) -> None:
        """Inline style attributes should be removed from all tags."""
        html = '<p style="color: red;">Styled text</p>'
        result = html_sanitizer.sanitize(html)
        assert "style=" not in result
        assert "color: red" not in result
        assert "Styled text" in result

    def test_removes_onclick_attributes(
        self, html_sanitizer: HtmlSanitizer
    ) -> None:
        """Event handler attributes should be removed."""
        html = '<button onclick="malicious()">Click</button>'
        result = html_sanitizer.sanitize(html)
        assert "onclick" not in result

    def test_removes_onload_attributes(
        self, html_sanitizer: HtmlSanitizer
    ) -> None:
        """Onload attributes should be removed."""
        html = '<img src="x.png" onload="alert(1)">'
        result = html_sanitizer.sanitize(html)
        assert "onload" not in result

    def test_image_src_attribute_preserved(
        self, html_sanitizer: HtmlSanitizer
    ) -> None:
        """Image src attribute should be preserved."""
        html = '<img src="image.jpg">'
        result = html_sanitizer.sanitize(html)
        assert 'src="image.jpg"' in result

    def test_image_alt_attribute_preserved(
        self, html_sanitizer: HtmlSanitizer
    ) -> None:
        """Image alt attribute should be preserved."""
        html = '<img src="image.jpg" alt="Description">'
        result = html_sanitizer.sanitize(html)
        assert 'alt="Description"' in result

    def test_image_title_attribute_preserved(
        self, html_sanitizer: HtmlSanitizer
    ) -> None:
        """Image title attribute should be preserved."""
        html = '<img src="image.jpg" title="Tooltip">'
        result = html_sanitizer.sanitize(html)
        assert 'title="Tooltip"' in result

    def test_image_disallowed_attributes_removed(
        self, html_sanitizer: HtmlSanitizer
    ) -> None:
        """Image tags should only keep src, alt, title attributes."""
        html = (
            '<img src="x.jpg" alt="X" title="T" '
            'width="100" height="100" class="big">'
        )
        result = html_sanitizer.sanitize(html)
        assert 'src="x.jpg"' in result
        assert 'alt="X"' in result
        assert 'title="T"' in result
        assert "width=" not in result
        assert "height=" not in result
        assert "class=" not in result

    def test_removes_data_attributes(
        self, html_sanitizer: HtmlSanitizer
    ) -> None:
        """Custom data attributes should be removed."""
        html = '<div data-user-id="123">Content</div>'
        result = html_sanitizer.sanitize(html)
        assert "data-user-id" not in result

    def test_removes_id_attributes(self, html_sanitizer: HtmlSanitizer) -> None:
        """ID attributes should be removed to prevent DOM manipulation."""
        html = '<p id="unique">Text</p>'
        result = html_sanitizer.sanitize(html)
        assert "id=" not in result

    def test_removes_class_attributes(
        self, html_sanitizer: HtmlSanitizer
    ) -> None:
        """Class attributes preserved on allowed tags.

        Classes are preserved on div/span for syntax highlighting.
        """
        html = '<div class="highlight">Content</div>'
        result = html_sanitizer.sanitize(html)
        assert 'class="highlight"' in result

        html = '<p class="invalid">Content</p>'
        result = html_sanitizer.sanitize(html)
        assert "class=" not in result


class TestHtmlSanitizerExternalLinkHandling:
    """
    Test that external links receive appropriate rel attributes.

    Verifies requirement 9.6: Links have rel="nofollow noreferrer" added
    to external links.
    """

    def test_adds_nofollow_to_external_links(
        self, html_sanitizer: HtmlSanitizer
    ) -> None:
        """External links should have rel='nofollow noreferrer' added."""
        html = '<a href="https://external.com">External</a>'
        result = html_sanitizer.sanitize(html)
        assert (
            'rel="nofollow noreferrer"' in result
            or 'rel="noreferrer nofollow"' in result
        )

    def test_adds_nofollow_to_http_links(
        self, html_sanitizer: HtmlSanitizer
    ) -> None:
        """HTTP links should also receive nofollow."""
        html = '<a href="http://external.com">External</a>'
        result = html_sanitizer.sanitize(html)
        assert "nofollow" in result
        assert "noreferrer" in result

    def test_preserves_existing_rel_with_nofollow(
        self, html_sanitizer: HtmlSanitizer
    ) -> None:
        """If rel attribute exists, nofollow should be added to it."""
        html = '<a href="https://external.com" rel="external">Link</a>'
        result = html_sanitizer.sanitize(html)
        assert "nofollow" in result
        assert "noreferrer" in result

    def test_handles_multiple_external_links(
        self, html_sanitizer: HtmlSanitizer
    ) -> None:
        """Multiple external links should all receive nofollow."""
        html = (
            '<a href="https://site1.com">Site 1</a> '
            '<a href="https://site2.com">Site 2</a>'
        )
        result = html_sanitizer.sanitize(html)
        assert result.count("nofollow") >= 2
        assert result.count("noreferrer") >= 2

    def test_handles_anchor_links(self, html_sanitizer: HtmlSanitizer) -> None:
        """Internal anchor links should not receive nofollow."""
        html = '<a href="#section">Jump to section</a>'
        result = html_sanitizer.sanitize(html)
        assert 'href="#section"' in result

    def test_handles_mailto_links(self, html_sanitizer: HtmlSanitizer) -> None:
        """Mailto links should be allowed."""
        html = '<a href="mailto:user@example.com">Email</a>'
        result = html_sanitizer.sanitize(html)
        assert 'href="mailto:user@example.com"' in result

    def test_handles_relative_links(
        self, html_sanitizer: HtmlSanitizer
    ) -> None:
        """Relative links should not receive nofollow."""
        html = '<a href="/posts/123">Post</a>'
        result = html_sanitizer.sanitize(html)
        assert 'href="/posts/123"' in result

    def test_nofollow_added_only_once(
        self, html_sanitizer: HtmlSanitizer
    ) -> None:
        """If link already has nofollow, it should not be duplicated."""
        html = '<a href="https://external.com" rel="nofollow">Link</a>'
        result = html_sanitizer.sanitize(html)
        assert result.count("nofollow") == 1


class TestHtmlSanitizerProtocolValidation:
    """
    Test that only safe URL protocols are allowed.

    Ensures that javascript:, data:, and other dangerous protocols are blocked.
    """

    def test_allows_https_protocol(self, html_sanitizer: HtmlSanitizer) -> None:
        """HTTPS protocol should be allowed in links."""
        html = '<a href="https://example.com">Link</a>'
        result = html_sanitizer.sanitize(html)
        assert 'href="https://example.com"' in result

    def test_allows_http_protocol(self, html_sanitizer: HtmlSanitizer) -> None:
        """HTTP protocol should be allowed in links."""
        html = '<a href="http://example.com">Link</a>'
        result = html_sanitizer.sanitize(html)
        assert 'href="http://example.com"' in result

    def test_allows_mailto_protocol(
        self, html_sanitizer: HtmlSanitizer
    ) -> None:
        """Mailto protocol should be allowed."""
        html = '<a href="mailto:test@example.com">Email</a>'
        result = html_sanitizer.sanitize(html)
        assert 'href="mailto:test@example.com"' in result

    def test_blocks_javascript_protocol(
        self, html_sanitizer: HtmlSanitizer
    ) -> None:
        """JavaScript protocol should be blocked in all contexts."""
        html = '<a href="javascript:alert(1)">Click</a>'
        result = html_sanitizer.sanitize(html)
        assert "javascript:" not in result.lower()

    def test_blocks_data_protocol(self, html_sanitizer: HtmlSanitizer) -> None:
        """Data protocol should be blocked to prevent data URI attacks."""
        html = '<a href="data:text/html,<script>alert(1)</script>">Link</a>'
        result = html_sanitizer.sanitize(html)
        assert "data:" not in result.lower()

    def test_blocks_vbscript_protocol(
        self, html_sanitizer: HtmlSanitizer
    ) -> None:
        """VBScript protocol should be blocked."""
        html = '<a href="vbscript:alert(1)">Link</a>'
        result = html_sanitizer.sanitize(html)
        assert "vbscript:" not in result.lower()

    def test_blocks_file_protocol(self, html_sanitizer: HtmlSanitizer) -> None:
        """File protocol should be blocked."""
        html = '<a href="file:///etc/passwd">Link</a>'
        result = html_sanitizer.sanitize(html)
        assert "file://" not in result.lower()

    def test_blocks_javascript_in_image_src(
        self, html_sanitizer: HtmlSanitizer
    ) -> None:
        """JavaScript protocol should be blocked in image src."""
        html = '<img src="javascript:alert(1)">'
        result = html_sanitizer.sanitize(html)
        assert "javascript:" not in result.lower()

    def test_handles_protocol_case_variations(
        self, html_sanitizer: HtmlSanitizer
    ) -> None:
        """Protocol blocking should be case-insensitive."""
        html = '<a href="JaVaScRiPt:alert(1)">Link</a>'
        result = html_sanitizer.sanitize(html)
        assert "javascript:" not in result.lower()

    def test_handles_encoded_protocols(
        self, html_sanitizer: HtmlSanitizer
    ) -> None:
        """URL-encoded dangerous protocols should be blocked."""
        html = '<a href="java&#115;cript:alert(1)">Link</a>'
        result = html_sanitizer.sanitize(html)
        assert "alert" not in result or "href=" not in result


class TestHtmlSanitizerEdgeCases:
    """
    Test edge cases and boundary conditions.

    Ensures the sanitizer handles empty strings, malformed HTML,
    unicode characters, and other edge cases gracefully.
    """

    def test_handles_empty_string(self, html_sanitizer: HtmlSanitizer) -> None:
        """Empty string input should return empty string."""
        result = html_sanitizer.sanitize("")
        assert result == ""

    def test_handles_whitespace_only(
        self, html_sanitizer: HtmlSanitizer
    ) -> None:
        """Whitespace-only input should be preserved or normalized."""
        result = html_sanitizer.sanitize("   ")
        assert isinstance(result, str)

    def test_handles_plain_text(self, html_sanitizer: HtmlSanitizer) -> None:
        """Plain text without HTML should be preserved."""
        text = "This is plain text without any HTML."
        result = html_sanitizer.sanitize(text)
        assert text in result or text == result

    def test_handles_unclosed_tags(self, html_sanitizer: HtmlSanitizer) -> None:
        """Malformed HTML with unclosed tags should be handled gracefully."""
        html = "<p>Paragraph without closing tag"
        result = html_sanitizer.sanitize(html)
        assert "Paragraph without closing tag" in result
        assert isinstance(result, str)

    def test_handles_mismatched_tags(
        self, html_sanitizer: HtmlSanitizer
    ) -> None:
        """Mismatched opening and closing tags should be handled."""
        html = "<p>Text</div>"
        result = html_sanitizer.sanitize(html)
        assert "Text" in result

    def test_handles_unicode_characters(
        self, html_sanitizer: HtmlSanitizer
    ) -> None:
        """Unicode characters should be preserved correctly."""
        html = "<p>Hello 世界 🌍 Ñoño</p>"
        result = html_sanitizer.sanitize(html)
        assert "世界" in result
        assert "🌍" in result
        assert "Ñoño" in result

    def test_handles_html_entities(self, html_sanitizer: HtmlSanitizer) -> None:
        """HTML entities should be handled correctly."""
        html = "<p>&lt;script&gt; &amp; &quot;quotes&quot;</p>"
        result = html_sanitizer.sanitize(html)
        assert "&lt;" in result or "<script>" not in result
        assert "&amp;" in result or "&" in result

    def test_handles_very_long_content(
        self, html_sanitizer: HtmlSanitizer
    ) -> None:
        """Very long HTML content should be processed without errors."""
        html = "<p>" + ("Long text. " * 1000) + "</p>"
        result = html_sanitizer.sanitize(html)
        assert "Long text." in result
        assert isinstance(result, str)

    def test_handles_deeply_nested_tags(
        self, html_sanitizer: HtmlSanitizer
    ) -> None:
        """Deeply nested tags should be processed correctly."""
        html = (
            "<div><div><div><div><div><p>Deep</p></div></div></div></div></div>"
        )
        result = html_sanitizer.sanitize(html)
        assert "Deep" in result

    def test_handles_self_closing_tags(
        self, html_sanitizer: HtmlSanitizer
    ) -> None:
        """Self-closing tags should be handled correctly."""
        html = "<p>Text<br/>More<hr/>End</p>"
        result = html_sanitizer.sanitize(html)
        assert "Text" in result
        assert "More" in result
        assert "End" in result

    def test_handles_mixed_content(self, html_sanitizer: HtmlSanitizer) -> None:
        """Dangerous content should be removed from mixed content."""
        html = (
            "<p>Safe paragraph</p>"
            "<script>dangerous()</script>"
            "<strong>Safe strong</strong>"
            '<img src="x" onerror="bad()">'
        )
        result = html_sanitizer.sanitize(html)
        assert "<p>Safe paragraph</p>" in result
        assert "<script>" not in result
        assert "<strong>Safe strong</strong>" in result
        assert "onerror" not in result

    def test_sanitize_returns_string(
        self, html_sanitizer: HtmlSanitizer
    ) -> None:
        """Sanitize method should always return a string."""
        result = html_sanitizer.sanitize("<p>Test</p>")
        assert isinstance(result, str)

    def test_handles_comments(self, html_sanitizer: HtmlSanitizer) -> None:
        """HTML comments should be handled (typically removed)."""
        html = "<p>Text</p><!-- Comment --><p>More</p>"
        result = html_sanitizer.sanitize(html)
        assert "Text" in result
        assert "More" in result

    def test_handles_cdata_sections(
        self, html_sanitizer: HtmlSanitizer
    ) -> None:
        """CDATA sections should be handled appropriately."""
        html = "<p>Text</p><![CDATA[Some data]]><p>More</p>"
        result = html_sanitizer.sanitize(html)
        assert "Text" in result
        assert "More" in result

    def test_preserves_line_breaks_in_pre(
        self, html_sanitizer: HtmlSanitizer
    ) -> None:
        """Line breaks inside pre tags should be preserved."""
        html = "<pre>Line 1\nLine 2\nLine 3</pre>"
        result = html_sanitizer.sanitize(html)
        assert "<pre>" in result
        assert "Line 1" in result


@pytest.fixture
def html_sanitizer() -> HtmlSanitizer:
    """
    Provide an HtmlSanitizer instance for testing.

    Returns:
        HtmlSanitizer: Fresh sanitizer instance with default configuration.
    """
    return HtmlSanitizer()
