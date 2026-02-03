"""
Unit tests for MarkdownRenderingService.

Tests cover requirements 9.1-9.2 from post-management spec:
- 9.1: markdown-it-py converts markdown to HTML
- 9.2: Pygments applies syntax highlighting to code blocks

Following TDD red phase - tests written before implementation.
Target coverage: 80%+
"""

import pytest


class TestMarkdownRenderingServiceBasicRendering:
    """Test basic markdown to HTML conversion."""

    def test_plain_text_renders_as_paragraph(self, markdown_service):
        """Plain text should be wrapped in paragraph tags."""
        markdown = "Hello, world!"
        html = markdown_service.render(markdown)
        assert "<p>Hello, world!</p>" in html
        assert html.strip().startswith("<p>")
        assert html.strip().endswith("</p>")

    def test_multiple_paragraphs_separated_by_blank_lines(
        self, markdown_service
    ):
        """Multiple paragraphs separated by blank lines create separate p
        tags."""
        markdown = "First paragraph.\n\nSecond paragraph."
        html = markdown_service.render(markdown)
        assert html.count("<p>") == 2
        assert html.count("</p>") == 2
        assert "First paragraph" in html
        assert "Second paragraph" in html

    def test_bold_text_renders_with_strong_tags(self, markdown_service):
        """Bold markdown (**text**) should render as <strong>."""
        markdown = "This is **bold** text."
        html = markdown_service.render(markdown)
        assert "<strong>bold</strong>" in html

    def test_italic_text_renders_with_em_tags(self, markdown_service):
        """Italic markdown (*text*) should render as <em>."""
        markdown = "This is *italic* text."
        html = markdown_service.render(markdown)
        assert "<em>italic</em>" in html

    def test_inline_code_renders_with_code_tags(self, markdown_service):
        """Inline code (`code`) should render as <code>."""
        markdown = "Use `print()` function."
        html = markdown_service.render(markdown)
        assert "<code>print()</code>" in html


class TestMarkdownRenderingServiceHeadings:
    """Test heading conversion from markdown to HTML."""

    def test_h1_heading_renders_correctly(self, markdown_service):
        """H1 heading (# text) should render as <h1>."""
        markdown = "# Main Title"
        html = markdown_service.render(markdown)
        assert "<h1>Main Title</h1>" in html

    def test_h2_heading_renders_correctly(self, markdown_service):
        """H2 heading (## text) should render as <h2>."""
        markdown = "## Section Title"
        html = markdown_service.render(markdown)
        assert "<h2>Section Title</h2>" in html

    def test_h3_heading_renders_correctly(self, markdown_service):
        """H3 heading (### text) should render as <h3>."""
        markdown = "### Subsection"
        html = markdown_service.render(markdown)
        assert "<h3>Subsection</h3>" in html

    def test_h4_heading_renders_correctly(self, markdown_service):
        """H4 heading (#### text) should render as <h4>."""
        markdown = "#### Minor Heading"
        html = markdown_service.render(markdown)
        assert "<h4>Minor Heading</h4>" in html

    def test_h5_heading_renders_correctly(self, markdown_service):
        """H5 heading (##### text) should render as <h5>."""
        markdown = "##### Small Heading"
        html = markdown_service.render(markdown)
        assert "<h5>Small Heading</h5>" in html

    def test_h6_heading_renders_correctly(self, markdown_service):
        """H6 heading (###### text) should render as <h6>."""
        markdown = "###### Smallest Heading"
        html = markdown_service.render(markdown)
        assert "<h6>Smallest Heading</h6>" in html

    def test_mixed_heading_levels(self, markdown_service):
        """Multiple heading levels should all render correctly."""
        markdown = "# Title\n\n## Section\n\n### Subsection"
        html = markdown_service.render(markdown)
        assert "<h1>Title</h1>" in html
        assert "<h2>Section</h2>" in html
        assert "<h3>Subsection</h3>" in html


class TestMarkdownRenderingServiceLists:
    """Test list rendering (ordered and unordered)."""

    def test_unordered_list_renders_with_ul_tags(self, markdown_service):
        """Unordered list should render as <ul> with <li> items."""
        markdown = "- Item 1\n- Item 2\n- Item 3"
        html = markdown_service.render(markdown)
        assert "<ul>" in html
        assert "</ul>" in html
        assert html.count("<li>") == 3
        assert html.count("</li>") == 3
        assert "Item 1" in html
        assert "Item 2" in html
        assert "Item 3" in html

    def test_ordered_list_renders_with_ol_tags(self, markdown_service):
        """Ordered list should render as <ol> with <li> items."""
        markdown = "1. First\n2. Second\n3. Third"
        html = markdown_service.render(markdown)
        assert "<ol>" in html
        assert "</ol>" in html
        assert html.count("<li>") == 3
        assert "First" in html
        assert "Second" in html
        assert "Third" in html

    def test_nested_unordered_lists(self, markdown_service):
        """Nested unordered lists should create nested <ul> tags."""
        markdown = "- Parent 1\n  - Child 1\n  - Child 2\n- Parent 2"
        html = markdown_service.render(markdown)
        assert html.count("<ul>") >= 2
        assert "Parent 1" in html
        assert "Child 1" in html
        assert "Child 2" in html
        assert "Parent 2" in html

    def test_nested_ordered_lists(self, markdown_service):
        """Nested ordered lists should create nested <ol> tags."""
        markdown = "1. First\n   1. Sub-first\n   2. Sub-second\n2. Second"
        html = markdown_service.render(markdown)
        assert html.count("<ol>") >= 2
        assert "First" in html
        assert "Sub-first" in html
        assert "Second" in html


class TestMarkdownRenderingServiceLinksAndImages:
    """Test link and image rendering."""

    def test_link_renders_with_anchor_tag(self, markdown_service):
        """Markdown link [text](url) should render as <a href="url">text</a>."""
        markdown = "[Click here](https://example.com)"
        html = markdown_service.render(markdown)
        assert '<a href="https://example.com">Click here</a>' in html

    def test_link_with_title_attribute(self, markdown_service):
        """Markdown link with title should include title attribute."""
        markdown = '[Link](https://example.com "Example Site")'
        html = markdown_service.render(markdown)
        assert "https://example.com" in html
        assert "Link" in html

    def test_image_renders_with_img_tag(self, markdown_service):
        """Markdown image ![alt](url) should render as <img>."""
        markdown = "![Alt text](https://example.com/image.png)"
        html = markdown_service.render(markdown)
        assert "<img" in html
        assert 'src="https://example.com/image.png"' in html
        assert 'alt="Alt text"' in html

    def test_image_with_title_attribute(self, markdown_service):
        """Markdown image with title should include title attribute."""
        markdown = '![Photo](https://example.com/photo.jpg "My Photo")'
        html = markdown_service.render(markdown)
        assert "<img" in html
        assert "https://example.com/photo.jpg" in html
        assert "Photo" in html


class TestMarkdownRenderingServiceCodeBlockSyntaxHighlighting:
    """
    Test syntax highlighting for code blocks using Pygments.

    CRITICAL: Requirements 9.2 - Pygments SHALL apply syntax highlighting.
    """

    def test_python_code_block_with_syntax_highlighting(self, markdown_service):
        """Python code block should be highlighted with Pygments."""
        markdown = "```python\ndef hello():\n    print('Hello, world!')\n```"
        html = markdown_service.render(markdown)

        assert "<pre>" in html or "<div" in html
        assert "def" in html
        assert "hello" in html
        assert "print" in html

        assert (
            'class="highlight"' in html
            or 'class="codehilite"' in html
            or "<span" in html
        )

    def test_javascript_code_block_with_syntax_highlighting(
        self, markdown_service
    ):
        """JavaScript code block should be highlighted with Pygments."""
        markdown = (
            "```javascript\n"
            "const greeting = 'Hello';\n"
            "console.log(greeting);\n"
            "```"
        )
        html = markdown_service.render(markdown)

        assert "const" in html
        assert "greeting" in html
        assert "console" in html

        assert (
            'class="highlight"' in html
            or 'class="codehilite"' in html
            or "<span" in html
        )

    def test_typescript_code_block_with_syntax_highlighting(
        self, markdown_service
    ):
        """TypeScript code block should be highlighted with Pygments."""
        markdown = "```typescript\ninterface User {\n  name: string;\n}\n```"
        html = markdown_service.render(markdown)

        assert "interface" in html
        assert "User" in html
        assert "string" in html

    def test_json_code_block_with_syntax_highlighting(self, markdown_service):
        """JSON code block should be highlighted with Pygments."""
        markdown = '```json\n{\n  "key": "value"\n}\n```'
        html = markdown_service.render(markdown)

        assert "key" in html
        assert "value" in html

    def test_code_block_without_language_hint(self, markdown_service):
        """Code block without language hint should still render as code."""
        markdown = "```\nplain code\nno language\n```"
        html = markdown_service.render(markdown)

        assert "<pre>" in html or "<code>" in html
        assert "plain code" in html
        assert "no language" in html

    def test_code_block_with_unknown_language(self, markdown_service):
        """Code block with unknown language should fallback gracefully."""
        markdown = "```unknownlang\nsome code here\n```"
        html = markdown_service.render(markdown)

        assert "<pre>" in html or "<code>" in html
        assert "some code here" in html

    def test_empty_code_block(self, markdown_service):
        """Empty code block should render without errors."""
        markdown = "```python\n```"
        html = markdown_service.render(markdown)

        assert "<pre>" in html or "<code>" in html

    def test_code_block_preserves_indentation(self, markdown_service):
        """Code block should preserve indentation and whitespace."""
        markdown = "```python\ndef func():\n    if True:\n        return 1\n```"
        html = markdown_service.render(markdown)

        assert "def" in html
        assert "func" in html
        assert "if" in html
        assert "True" in html
        assert "return" in html

    def test_multiple_code_blocks_in_document(self, markdown_service):
        """Multiple code blocks should all be highlighted independently."""
        markdown = """
# Code Examples

Python:
```python
x = 1
```

JavaScript:
```javascript
const y = 2;
```
"""
        html = markdown_service.render(markdown)

        assert html.count("<pre>") >= 2 or html.count("<code>") >= 2
        assert "x" in html and "1" in html
        assert "const" in html and "y" in html and "2" in html

    def test_inline_code_not_highlighted(self, markdown_service):
        """Inline code should not receive Pygments highlighting."""
        markdown = "Use `print()` function in Python."
        html = markdown_service.render(markdown)

        assert "<code>print()</code>" in html
        assert (
            'class="highlight"' not in html
            or html.count('class="highlight"') == 0
        )

    def test_code_block_with_cpp_language(self, markdown_service):
        """C++ language should be highlighted."""
        markdown = "```c++\nstd::vector<int> v;\n```"
        html = markdown_service.render(markdown)
        assert "std" in html
        assert "vector" in html
        assert "highlight" in html

    def test_code_block_with_csharp_language(self, markdown_service):
        """C# language should be highlighted."""
        markdown = "```c#\npublic class Test {}\n```"
        html = markdown_service.render(markdown)
        assert "public" in html
        assert "class" in html
        assert "highlight" in html


class TestMarkdownRenderingServiceEdgeCases:
    """Test edge cases and error handling."""

    def test_empty_string_returns_empty_string(self, markdown_service):
        """Empty input should return empty string."""
        markdown = ""
        html = markdown_service.render(markdown)
        assert html == ""

    def test_only_whitespace_handled_gracefully(self, markdown_service):
        """Input with only whitespace should be handled gracefully."""
        markdown = "   \n\n   \t\n"
        html = markdown_service.render(markdown)
        assert isinstance(html, str)

    def test_unicode_characters_preserved(self, markdown_service):
        """Unicode characters should be preserved in output."""
        markdown = "Hello 世界! 🌍 Emoji test."
        html = markdown_service.render(markdown)
        assert "世界" in html
        assert "🌍" in html

    def test_html_like_content_in_code_block_escaped(self, markdown_service):
        """HTML-like content in code blocks should be properly escaped."""
        markdown = "```html\n<div>Hello</div>\n```"
        html = markdown_service.render(markdown)

        assert "&lt;" in html and "div" in html and "&gt;" in html
        assert "Hello" in html

    def test_special_markdown_characters_in_code_block(self, markdown_service):
        """Special markdown characters in code blocks should not be
        processed."""
        markdown = "```\n**not bold**\n*not italic*\n```"
        html = markdown_service.render(markdown)

        assert "**not bold**" in html
        assert "*not italic*" in html
        assert "<strong>" not in html
        assert "<em>" not in html

    def test_very_long_markdown_document(self, markdown_service):
        """Very long markdown document should render without errors."""
        markdown = "\n\n".join(
            [f"# Heading {i}\n\nParagraph {i}" for i in range(100)]
        )
        html = markdown_service.render(markdown)

        assert html.count("<h1>") == 100
        assert html.count("<p>") == 100

    def test_nested_formatting_combinations(self, markdown_service):
        """Nested formatting should render correctly."""
        markdown = "**This is *bold and italic* text**"
        html = markdown_service.render(markdown)

        assert "<strong>" in html
        assert "<em>" in html
        assert "bold and italic" in html

    def test_blockquote_rendering(self, markdown_service):
        """Blockquotes should render with <blockquote> tags."""
        markdown = "> This is a quote\n> Multi-line quote"
        html = markdown_service.render(markdown)

        assert "<blockquote>" in html
        assert "</blockquote>" in html
        assert "This is a quote" in html

    def test_horizontal_rule_rendering(self, markdown_service):
        """Horizontal rules should render as <hr>."""
        markdown = "Text above\n\n---\n\nText below"
        html = markdown_service.render(markdown)

        assert "<hr" in html or "<hr>" in html
        assert "Text above" in html
        assert "Text below" in html


class TestMarkdownRenderingServiceComplexDocuments:
    """Test rendering of complex, realistic markdown documents."""

    def test_blog_post_structure(self, markdown_service):
        """Realistic blog post with mixed elements should render correctly."""
        markdown = """# My Blog Post

This is the introduction paragraph.

## Code Example

Here's some Python:

```python
def calculate_sum(a, b):
    return a + b
```

## Lists

Key features:
- Fast performance
- Easy to use
- **Well documented**

## Conclusion

Visit [my website](https://example.com) for more!
"""
        html = markdown_service.render(markdown)

        assert "<h1>My Blog Post</h1>" in html
        assert "<h2>Code Example</h2>" in html
        assert "def" in html and "calculate_sum" in html
        assert "<ul>" in html
        assert "<strong>Well documented</strong>" in html
        assert "https://example.com" in html

    def test_technical_documentation_structure(self, markdown_service):
        """Technical documentation with code blocks and nested lists."""
        markdown = """# API Documentation

## Installation

1. Install dependencies:
   ```bash
   pip install package
   ```
2. Configure settings
3. Run the application

## Usage

```python
from package import Client

client = Client(api_key="secret")
result = client.fetch_data()
```

### Response Format

```json
{
  "status": "success",
  "data": []
}
```
"""
        html = markdown_service.render(markdown)

        assert "<h1>API Documentation</h1>" in html
        assert "<ol>" in html
        assert "pip" in html and "install" in html and "package" in html
        assert "from" in html and "package" in html and "Client" in html
        assert "status" in html and "success" in html


@pytest.fixture
def markdown_service():
    """
    Fixture providing MarkdownRenderingService instance.

    This will fail initially until the service is implemented (TDD red phase).
    """
    from backend.infrastructure.markdown.markdown_rendering_service import (
        MarkdownRenderingService,
    )

    return MarkdownRenderingService()
