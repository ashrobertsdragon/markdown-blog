"""Unit tests for DraftFile YAML serialization/deserialization."""

from datetime import UTC, datetime

import pytest
from backend.infrastructure.persistence.filesystem_draft_repository import (
    DraftFile,
)


def test_draft_file_to_markdown_serializes_front_matter() -> None:
    """Verify to_markdown() creates valid YAML front matter."""
    draft = DraftFile(
        slug="test-post",
        title="Test Post",
        author="user123",
        content="This is the content.",
        published=False,
        created_at=datetime(2026, 1, 19, 12, 0, 0, tzinfo=UTC),
        tags=["python", "testing"],
    )

    markdown = draft.to_markdown()

    assert markdown.startswith("---\n")
    assert "title: Test Post" in markdown
    assert "author: user123" in markdown
    assert "published: false" in markdown
    assert "tags:\n- python\n- testing" in markdown
    assert "\n---\n\nThis is the content." in markdown


def test_draft_file_from_markdown_parses_front_matter() -> None:
    """Verify from_markdown() correctly parses YAML."""
    markdown = """---
title: My Post
author: alice
created_at: '2026-01-19T12:00:00+00:00'
published: false
tags:
- blog
- tech
---

Post content here."""

    draft = DraftFile.from_markdown(markdown, slug="my-post")

    assert draft.slug == "my-post"
    assert draft.title == "My Post"
    assert draft.author == "alice"
    assert draft.content == "Post content here."
    assert draft.published is False
    assert draft.created_at == datetime(2026, 1, 19, 12, 0, 0, tzinfo=UTC)
    assert draft.tags == ["blog", "tech"]
    assert draft.published_at is None


def test_draft_file_round_trip_preserves_data() -> None:
    """Verify data survives serialize → deserialize cycle."""
    original = DraftFile(
        slug="round-trip",
        title="Round Trip Test",
        author="bob",
        content="Original content\nWith multiple lines.",
        published=False,
        created_at=datetime(2026, 1, 19, 10, 30, 0, tzinfo=UTC),
        tags=["test"],
    )

    markdown = original.to_markdown()
    restored = DraftFile.from_markdown(markdown, slug="round-trip")

    assert restored.slug == original.slug
    assert restored.title == original.title
    assert restored.author == original.author
    assert restored.content == original.content
    assert restored.published == original.published
    assert restored.created_at == original.created_at
    assert restored.tags == original.tags


def test_draft_file_to_markdown_format() -> None:
    """Verify YAML format is: ---\\nyaml---\\n\\ncontent."""
    draft = DraftFile(
        slug="format-test",
        title="Format",
        author="user",
        content="Content",
        published=False,
        created_at=datetime(2026, 1, 19, 12, 0, 0, tzinfo=UTC),
    )

    markdown = draft.to_markdown()
    parts = markdown.split("---")

    assert len(parts) == 3
    assert parts[0] == ""
    assert parts[1].strip()
    assert parts[2].strip() == "Content"


def test_draft_file_front_matter_includes_all_fields() -> None:
    """Verify front matter has: title, author, created_at, published, tags."""
    draft = DraftFile(
        slug="complete",
        title="Complete Post",
        author="charlie",
        content="Full content",
        published=True,
        created_at=datetime(2026, 1, 19, 12, 0, 0, tzinfo=UTC),
        published_at=datetime(2026, 1, 19, 14, 0, 0, tzinfo=UTC),
        tags=["complete"],
    )

    markdown = draft.to_markdown()

    assert "title: Complete Post" in markdown
    assert "author: charlie" in markdown
    assert "created_at:" in markdown
    assert "published: true" in markdown
    assert "published_at:" in markdown
    assert "tags:\n- complete" in markdown


def test_draft_file_missing_front_matter_raises_error() -> None:
    """Verify from_markdown() raises ValueError if no '---'."""
    invalid_markdown = "Just some content without front matter"

    with pytest.raises(
        ValueError,
        match="Invalid draft file: missing front matter",
    ):
        DraftFile.from_markdown(invalid_markdown, slug="invalid")


def test_draft_file_timestamps_in_iso_format() -> None:
    """Verify created_at and published_at use ISO format."""
    draft = DraftFile(
        slug="timestamps",
        title="Timestamp Test",
        author="dave",
        content="Content",
        published=True,
        created_at=datetime(2026, 1, 19, 12, 30, 45, tzinfo=UTC),
        published_at=datetime(2026, 1, 19, 15, 0, 0, tzinfo=UTC),
    )

    markdown = draft.to_markdown()

    assert "created_at: '2026-01-19T12:30:45+00:00'" in markdown
    assert "published_at: '2026-01-19T15:00:00+00:00'" in markdown


def test_draft_file_published_at_optional() -> None:
    """Verify published_at can be None when not published."""
    draft = DraftFile(
        slug="unpublished",
        title="Unpublished",
        author="eve",
        content="Draft content",
        published=False,
        created_at=datetime(2026, 1, 19, 12, 0, 0, tzinfo=UTC),
    )

    markdown = draft.to_markdown()

    assert "published_at" not in markdown
    assert draft.published_at is None


def test_draft_file_empty_tags_list_by_default() -> None:
    """Verify tags default to empty list if not provided."""
    markdown = """---
title: No Tags
author: frank
created_at: '2026-01-19T12:00:00+00:00'
published: false
---

Content without tags."""

    draft = DraftFile.from_markdown(markdown, slug="no-tags")

    assert draft.tags == []


def test_draft_file_preserves_multiline_content() -> None:
    """Verify multiline markdown content is preserved correctly."""
    content = """# Heading

Paragraph one.

Paragraph two with **bold** text.

- List item 1
- List item 2"""

    draft = DraftFile(
        slug="multiline",
        title="Multiline",
        author="grace",
        content=content,
        published=False,
        created_at=datetime(2026, 1, 19, 12, 0, 0, tzinfo=UTC),
    )

    markdown = draft.to_markdown()
    restored = DraftFile.from_markdown(markdown, slug="multiline")

    assert restored.content == content


def test_draft_file_handles_empty_content() -> None:
    """Verify empty content is handled correctly."""
    draft = DraftFile(
        slug="empty",
        title="Empty Content",
        author="harry",
        content="",
        published=False,
        created_at=datetime(2026, 1, 19, 12, 0, 0, tzinfo=UTC),
    )

    markdown = draft.to_markdown()
    restored = DraftFile.from_markdown(markdown, slug="empty")

    assert restored.content == ""


def test_draft_file_from_markdown_with_published_post() -> None:
    """Verify parsing published post with published_at timestamp."""
    markdown = """---
title: Published Post
author: iris
created_at: '2026-01-19T10:00:00+00:00'
published: true
published_at: '2026-01-19T12:00:00+00:00'
tags:
- published
---

This post is published."""

    draft = DraftFile.from_markdown(markdown, slug="published")

    assert draft.published is True
    assert draft.published_at == datetime(2026, 1, 19, 12, 0, 0, tzinfo=UTC)


def test_draft_file_handles_special_chars_in_title() -> None:
    """Verify special characters in title are preserved."""
    draft = DraftFile(
        slug="special-chars",
        title='Post with: colons, quotes "test", and symbols!',
        author="jake",
        content="Content",
        published=False,
        created_at=datetime(2026, 1, 19, 12, 0, 0, tzinfo=UTC),
    )

    markdown = draft.to_markdown()
    restored = DraftFile.from_markdown(markdown, slug="special-chars")

    assert restored.title == draft.title
