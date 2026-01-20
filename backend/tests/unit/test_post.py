"""Unit tests for Post aggregate.

This module defines comprehensive tests for the Post aggregate following TDD
Red phase principles. These tests will initially fail until the Post aggregate
is implemented.

Test Coverage:
- Factory method tests (5 tests)
- State transition tests (6 tests)
- Edge case tests (3 tests)
"""

import datetime as dt
from datetime import datetime

import pytest
from backend.domain.aggregates.post import Post


def test_create_draft_sets_correct_fields() -> None:
    """Verify factory method sets all fields correctly.

    This test ensures that when creating a draft Post, all required fields
    are populated with the expected values. The factory method should accept
    slug string, title, and author_id, initializing the Post with proper
    defaults for unpublished state.
    """
    slug_str = "my-first-post"
    title = "My First Post"
    author_id = 42

    post = Post.create_draft(slug_str, title, author_id)

    assert str(post.slug) == slug_str
    assert post.title == title
    assert post.author_id == author_id
    assert post.html_content is None
    assert post.published is False
    assert post.published_at is None


def test_create_draft_has_timestamps() -> None:
    """Verify created_at and updated_at are set to current UTC time.

    This test ensures audit trail requirements: both created_at and
    updated_at fields must be automatically populated with the current
    UTC timestamp when a draft is created. Timestamps must be recent
    and within 1 second of creation time.
    """
    before = datetime.now(dt.UTC)
    post = Post.create_draft("test-post", "Test Post", 1)
    after = datetime.now(dt.UTC)

    assert before <= post.created_at <= after
    assert before <= post.updated_at <= after
    assert (post.created_at - before).total_seconds() < 1
    assert (post.updated_at - before).total_seconds() < 1


def test_create_draft_with_invalid_slug_raises_error() -> None:
    """Verify Slug validation errors propagate.

    This test ensures that slug validation happens at creation time.
    Invalid slugs (empty strings, too long, special characters only)
    should raise ValueError from the Slug value object, preventing
    creation of invalid Post aggregates.
    """
    with pytest.raises(ValueError, match="Slug cannot be empty"):
        Post.create_draft("", "Valid Title", 1)


def test_create_draft_with_empty_title_raises_error() -> None:
    """Verify empty title validation.

    This test enforces business rule: posts must have a non-empty title.
    Creating a Post with an empty or whitespace-only title should raise
    ValueError at the domain boundary to prevent invalid aggregates.
    """
    with pytest.raises(ValueError, match="title"):
        Post.create_draft("valid-slug", "", 1)

    with pytest.raises(ValueError, match="title"):
        Post.create_draft("valid-slug", "   ", 1)


def test_create_draft_with_invalid_author_id_raises_error() -> None:
    """Verify author_id > 0 validation.

    This test enforces business rule: author_id must be a positive integer
    referencing a valid user. Zero or negative values should raise ValueError
    since they cannot represent valid user references.
    """
    with pytest.raises(ValueError, match="author_id"):
        Post.create_draft("valid-slug", "Valid Title", 0)

    with pytest.raises(ValueError, match="author_id"):
        Post.create_draft("valid-slug", "Valid Title", -1)


def test_publish_sets_published_state() -> None:
    """Verify publish() transitions draft to published.

    This test validates the core publishing workflow: calling publish()
    with HTML content should set the published flag to True, making the
    post visible to readers. This is the primary state transition for Posts.
    """
    post = Post.create_draft("test-publish", "Test Publish", 1)
    assert post.published is False

    post.publish("<p>Published content</p>")

    assert post.published is True


def test_publish_sets_published_at_timestamp() -> None:
    """Verify published_at set to current time.

    This test ensures audit trail requirements: the published_at field
    must be automatically populated with the current UTC timestamp when
    a post is published. This timestamp records when the post became
    publicly visible and must be recent.
    """
    post = Post.create_draft("timestamp-test", "Timestamp Test", 1)
    assert post.published_at is None

    before = datetime.now(dt.UTC)
    post.publish("<p>Content</p>")
    after = datetime.now(dt.UTC)

    assert post.published_at is not None
    assert before <= post.published_at <= after
    assert (post.published_at - before).total_seconds() < 1


def test_publish_updates_updated_at() -> None:
    """Verify updated_at updated on publish.

    This test ensures change tracking: publishing a post should update
    the updated_at timestamp to reflect the modification. This supports
    tracking when posts were last changed regardless of operation type.
    """
    post = Post.create_draft("update-test", "Update Test", 1)
    original_updated_at = post.updated_at

    post.publish("<p>New content</p>")

    assert post.updated_at > original_updated_at


def test_unpublish_sets_published_false() -> None:
    """Verify unpublish() hides published post.

    This test validates the unpublishing workflow: calling unpublish()
    should set published flag to False, hiding the post from public view.
    This allows authors to retract published content without deleting it.
    """
    post = Post.create_draft("unpublish-test", "Unpublish Test", 1)
    post.publish("<p>Content</p>")
    assert post.published is True

    post.unpublish()

    assert post.published is False


def test_unpublish_preserves_published_at() -> None:
    """Verify historical published_at preserved.

    This test ensures audit trail integrity: unpublishing a post should
    NOT clear the published_at timestamp. The historical record of when
    the post was first published must be preserved for audit purposes.
    """
    post = Post.create_draft("preserve-test", "Preserve Test", 1)
    post.publish("<p>Content</p>")
    original_published_at = post.published_at

    post.unpublish()

    assert post.published_at == original_published_at
    assert post.published_at is not None


def test_unpublish_preserves_html_content() -> None:
    """Verify HTML kept for re-publication.

    This test ensures content preservation: unpublishing should NOT delete
    the HTML content. The content must be preserved to support re-publishing
    the same content later without requiring re-generation from markdown.
    """
    post = Post.create_draft("content-test", "Content Test", 1)
    html = "<p>Important content</p>"
    post.publish(html)

    post.unpublish()

    assert str(post.html_content) == html


def test_publish_with_none_html_raises_error() -> None:
    """Verify None HTML rejected.

    This test enforces business rule: published posts must have HTML content.
    Attempting to publish with None HTML should raise ValueError since
    there would be no content to display to readers.
    """
    post = Post.create_draft("none-html", "None HTML Test", 1)

    with pytest.raises(ValueError, match="html_content"):
        post.publish(None)  # type: ignore[arg-type]


def test_publish_with_empty_html_accepted() -> None:
    """Verify empty HTML allowed.

    This test validates edge case handling: publishing with empty string
    HTML should succeed. While unusual, empty content is technically valid
    and may be used for placeholder posts or special formatting cases.
    """
    post = Post.create_draft("empty-html", "Empty HTML Test", 1)

    post.publish("")

    assert post.published is True
    assert str(post.html_content) == ""


def test_unpublish_unpublished_post_is_idempotent() -> None:
    """Verify unpublishing already unpublished post succeeds.

    This test ensures defensive programming: calling unpublish() on a
    draft or already-unpublished post should succeed without errors.
    Idempotent operations simplify calling code that may not check
    current state before unpublishing.
    """
    post = Post.create_draft("idempotent-test", "Idempotent Test", 1)
    assert post.published is False

    post.unpublish()

    assert post.published is False
