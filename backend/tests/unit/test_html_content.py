"""Unit tests for HtmlContent value object.

Tests verify that HtmlContent correctly stores sanitized HTML as an immutable
value object, preserves all HTML structure and attributes, validates input,
and supports usage in collections.
"""

import pytest

from backend.domain.value_objects.html_content import HtmlContent


def test_html_content_stores_html_string() -> None:
    """Verify HtmlContent stores basic HTML exactly as provided."""
    html = "<p>This is a paragraph.</p>"
    content = HtmlContent(html)
    assert str(content) == "<p>This is a paragraph.</p>"


def test_html_content_preserves_html_structure() -> None:
    """Verify complex HTML with multiple nested tags is preserved."""
    html = (
        "<div><h1>Title</h1><p>Paragraph with <strong>bold</strong> "
        "and <em>italic</em>.</p><ul><li>Item 1</li><li>Item 2</li>"
        "</ul></div>"
    )
    content = HtmlContent(html)
    expected = (
        "<div><h1>Title</h1><p>Paragraph with <strong>bold</strong> "
        "and <em>italic</em>.</p><ul><li>Item 1</li><li>Item 2</li>"
        "</ul></div>"
    )
    assert str(content) == expected


def test_html_content_preserves_attributes() -> None:
    """Verify HTML attributes like href, src, and alt are preserved."""
    html = (
        '<a href="https://example.com">Link</a>'
        '<img src="/image.jpg" alt="Description">'
        '<p class="highlight">Text</p>'
    )
    content = HtmlContent(html)
    expected = (
        '<a href="https://example.com">Link</a>'
        '<img src="/image.jpg" alt="Description">'
        '<p class="highlight">Text</p>'
    )
    assert str(content) == expected


def test_html_content_accepts_empty_string() -> None:
    """Verify empty string is valid since drafts can be initially empty."""
    content = HtmlContent("")
    assert str(content) == ""


def test_html_content_value_cannot_be_changed_after_creation() -> None:
    """Verify HtmlContent is immutable after creation."""
    content = HtmlContent("<p>Original HTML</p>")
    with pytest.raises(AttributeError):
        content.value = "<p>Modified HTML</p>"


def test_html_content_raises_typeerror_for_none_input() -> None:
    """Verify None input raises TypeError since HTML cannot be None."""
    with pytest.raises(TypeError):
        HtmlContent(None)


def test_html_content_instances_are_hashable() -> None:
    """Verify HtmlContent instances can be stored in sets."""
    content1 = HtmlContent("<p>First post</p>")
    content2 = HtmlContent("<p>Second post</p>")
    content_set = {content1, content2}
    assert len(content_set) == 2
    assert content1 in content_set
    assert content2 in content_set


def test_html_content_instances_can_be_used_as_dict_keys() -> None:
    """Verify HtmlContent instances can be used as dictionary keys."""
    content1 = HtmlContent("<h1>Key 1</h1>")
    content2 = HtmlContent("<h1>Key 2</h1>")
    content_dict = {content1: "value1", content2: "value2"}
    assert content_dict[content1] == "value1"
    assert content_dict[content2] == "value2"


def test_html_content_equality_comparison_works() -> None:
    """Verify two instances with same HTML are equal."""
    content1 = HtmlContent("<p>Same content</p>")
    content2 = HtmlContent("<p>Same content</p>")
    content3 = HtmlContent("<p>Different content</p>")

    assert content1 == content2
    assert content1 != content3
    assert content2 != content3


def test_html_content_str_returns_value() -> None:
    """Verify __str__ returns the HTML content."""
    html = "<h1>Header</h1><p>Paragraph.</p>"
    content = HtmlContent(html)
    assert str(content) == "<h1>Header</h1><p>Paragraph.</p>"


def test_html_content_accepts_very_long_html() -> None:
    """Verify HtmlContent can store very long HTML documents."""
    long_html = "<p>" + ("a" * 10000) + "</p>"
    content = HtmlContent(long_html)
    assert len(str(content)) == 10007
    assert str(content) == long_html


def test_html_content_preserves_whitespace() -> None:
    """Verify whitespace including indentation and newlines are preserved."""
    html = """<div>
    <h1>Title</h1>
    <p>
        Paragraph with spaces.
    </p>
</div>"""
    content = HtmlContent(html)
    expected = """<div>
    <h1>Title</h1>
    <p>
        Paragraph with spaces.
    </p>
</div>"""
    assert str(content) == expected


def test_html_content_preserves_unicode() -> None:
    """Verify UTF-8 characters including emoji are preserved."""
    html = "<p>Hello 世界! 🚀 Testing unicode: café, naïve, Москва</p>"
    content = HtmlContent(html)
    assert (
        str(content)
        == "<p>Hello 世界! 🚀 Testing unicode: café, naïve, Москва</p>"
    )


def test_html_content_accepts_single_tag() -> None:
    """Verify minimal HTML with a single tag is accepted."""
    content = HtmlContent("<p>Text</p>")
    assert str(content) == "<p>Text</p>"
