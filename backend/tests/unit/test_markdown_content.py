"""Unit tests for MarkdownContent value object.

Tests verify that MarkdownContent correctly stores raw markdown text as an
immutable value object, preserves all content exactly as provided, validates
input, and supports usage in collections.
"""

import pytest

from backend.domain.value_objects.markdown_content import MarkdownContent


def test_markdown_content_stores_raw_text() -> None:
    """Verify MarkdownContent stores simple text exactly as provided."""
    content = MarkdownContent("This is a simple post.")
    assert str(content) == "This is a simple post."


def test_markdown_content_preserves_newlines() -> None:
    """Verify multiline content is preserved with all newlines intact."""
    markdown = "Line 1\nLine 2\n\nLine 3"
    content = MarkdownContent(markdown)
    assert str(content) == "Line 1\nLine 2\n\nLine 3"


def test_markdown_content_preserves_special_characters() -> None:
    """Verify special markdown syntax like code blocks are preserved."""
    markdown = "```python\nprint('hello')\n```\n\nUse `code` here."
    content = MarkdownContent(markdown)
    expected = "```python\nprint('hello')\n```\n\nUse `code` here."
    assert str(content) == expected


def test_markdown_content_accepts_empty_string() -> None:
    """Verify empty string is valid since drafts can be initially empty."""
    content = MarkdownContent("")
    assert str(content) == ""


def test_markdown_content_preserves_yaml_syntax() -> None:
    """Verify YAML front matter syntax is preserved exactly."""
    markdown = "---\ntitle: My Post\ndate: 2024-01-01\n---\n\nContent here."
    content = MarkdownContent(markdown)
    assert (
        str(content)
        == "---\ntitle: My Post\ndate: 2024-01-01\n---\n\nContent here."
    )


def test_markdown_content_preserves_unicode() -> None:
    """Verify UTF-8 characters including emoji are preserved."""
    markdown = "Hello 世界! 🚀 Testing unicode: café, naïve, Москва"
    content = MarkdownContent(markdown)
    assert str(content) == "Hello 世界! 🚀 Testing unicode: café, naïve, Москва"


def test_markdown_content_raises_typeerror_for_none_input() -> None:
    """Verify None input raises TypeError since markdown cannot be None."""
    with pytest.raises(TypeError):
        MarkdownContent(None)


def test_markdown_content_value_cannot_be_changed_after_creation() -> None:
    """Verify MarkdownContent is immutable after creation."""
    content = MarkdownContent("Original content")
    with pytest.raises(AttributeError):
        content.value = "Modified content"


def test_markdown_content_instances_are_hashable() -> None:
    """Verify MarkdownContent instances can be stored in sets."""
    content1 = MarkdownContent("First post")
    content2 = MarkdownContent("Second post")
    content_set = {content1, content2}
    assert len(content_set) == 2
    assert content1 in content_set
    assert content2 in content_set


def test_markdown_content_instances_can_be_used_as_dict_keys() -> None:
    """Verify MarkdownContent instances can be used as dictionary keys."""
    content1 = MarkdownContent("Key 1")
    content2 = MarkdownContent("Key 2")
    content_dict = {content1: "value1", content2: "value2"}
    assert content_dict[content1] == "value1"
    assert content_dict[content2] == "value2"


def test_markdown_content_str_returns_value() -> None:
    """Verify __str__ returns the raw markdown content."""
    markdown = "# Header\n\nParagraph."
    content = MarkdownContent(markdown)
    assert str(content) == "# Header\n\nParagraph."


def test_markdown_content_repr_shows_representation() -> None:
    """Verify __repr__ shows proper class representation."""
    content = MarkdownContent("Test content")
    assert repr(content) == "MarkdownContent(value='Test content')"


def test_markdown_content_equality_comparison_works() -> None:
    """Verify two instances with same content are equal."""
    content1 = MarkdownContent("Same content")
    content2 = MarkdownContent("Same content")
    content3 = MarkdownContent("Different content")

    assert content1 == content2
    assert content1 != content3
    assert content2 != content3


def test_markdown_content_accepts_very_long_markdown() -> None:
    """Verify MarkdownContent can store very long markdown documents."""
    long_markdown = "a" * 10000
    content = MarkdownContent(long_markdown)
    assert len(str(content)) == 10000
    assert str(content) == long_markdown
