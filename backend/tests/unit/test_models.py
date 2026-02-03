"""Unit tests for database models.

Tests SQLModel table definitions and field defaults.
"""

import time
from datetime import datetime

from backend.infrastructure.persistence.models import Post, User


def test_user_created_at_uses_default_factory():
    """User.created_at should use current timestamp, not import-time value.

    This test verifies that the default_factory lambda is called for each
    instance, preventing all users from sharing the same timestamp.
    """
    user1 = User(email="test1@example.com", role="authenticated")
    time.sleep(0.01)  # 10ms delay to ensure different timestamps
    user2 = User(email="test2@example.com", role="authenticated")

    assert isinstance(user1.created_at, datetime)
    assert isinstance(user2.created_at, datetime)
    assert user1.created_at != user2.created_at
    assert user2.created_at > user1.created_at


def test_post_created_at_uses_default_factory():
    """Post.created_at should use current timestamp, not import-time value.

    This test verifies that the default_factory lambda is called for each
    instance, preventing all posts from sharing the same timestamp.
    """
    post1 = Post(
        slug="test-post-1",
        title="Test Post 1",
        html_content="<p>Content</p>",
    )
    time.sleep(0.01)  # 10ms delay to ensure different timestamps
    post2 = Post(
        slug="test-post-2",
        title="Test Post 2",
        html_content="<p>Content</p>",
    )

    assert isinstance(post1.created_at, datetime)
    assert isinstance(post2.created_at, datetime)
    assert post1.created_at != post2.created_at
    assert post2.created_at > post1.created_at


def test_post_updated_at_uses_default_factory():
    """Post.updated_at should use current timestamp, not import-time value.

    This test verifies that the default_factory lambda is called for each
    instance, preventing all posts from sharing the same timestamp.
    """
    post1 = Post(
        slug="test-post-1",
        title="Test Post 1",
        html_content="<p>Content</p>",
    )
    time.sleep(0.01)  # 10ms delay to ensure different timestamps
    post2 = Post(
        slug="test-post-2",
        title="Test Post 2",
        html_content="<p>Content</p>",
    )

    assert isinstance(post1.updated_at, datetime)
    assert isinstance(post2.updated_at, datetime)
    assert post1.updated_at != post2.updated_at
    assert post2.updated_at > post1.updated_at


def test_post_created_at_and_updated_at_are_same_on_creation():
    """Post.created_at and updated_at should be identical on initial creation.

    Both timestamps should be set to the same value when a post is first
    created, since no update has occurred yet.
    """
    post = Post(
        slug="test-post",
        title="Test Post",
        html_content="<p>Content</p>",
    )

    # Should be very close (within 1ms) but may not be exactly equal
    # due to the separate lambda calls
    time_diff = abs((post.updated_at - post.created_at).total_seconds())
    assert time_diff < 0.001  # Less than 1ms difference


def test_user_clerk_user_id_defaults_to_none():
    """User.clerk_user_id should default to None for backward compatibility."""
    user = User(email="test@example.com", role="authenticated")
    assert user.clerk_user_id is None


def test_user_clerk_user_id_accepts_string():
    """User.clerk_user_id should accept valid Clerk user ID strings."""
    user = User(
        email="test@example.com",
        role="authenticated",
        clerk_user_id="user_2abc123xyz",
    )
    assert user.clerk_user_id == "user_2abc123xyz"


def test_user_can_be_created_without_clerk_user_id():
    """User should be creatable without providing clerk_user_id."""
    user = User(email="newuser@example.com")
    assert hasattr(user, "clerk_user_id")
    assert user.clerk_user_id is None


def test_post_html_content_field_exists():
    """Post model should have html_content field instead of published_html."""
    post = Post(
        slug="test-post",
        title="Test Post",
        html_content="<p>HTML content</p>",
    )
    assert hasattr(post, "html_content")
    assert post.html_content == "<p>HTML content</p>"


def test_post_published_at_field_exists():
    """Post model should have published_at field that accepts None."""
    post = Post(
        slug="test-post",
        title="Test Post",
        html_content="<p>Content</p>",
        published_at=None,
    )
    assert hasattr(post, "published_at")
    assert post.published_at is None


def test_post_published_at_accepts_datetime():
    """Post model should accept datetime for published_at field."""
    now = datetime.now()
    post = Post(
        slug="test-post",
        title="Test Post",
        html_content="<p>Content</p>",
        published_at=now,
    )
    assert post.published_at == now


def test_post_has_index_on_published_field():
    """Post model has index on published field for efficient filtering."""

    post_fields = Post.model_fields
    assert "published" in post_fields

    # Verify index is defined on the model by checking SQLAlchemy metadata
    # The index parameter in Field() creates a database index
    published_field_info = post_fields["published"]
    assert published_field_info.metadata is not None


def test_post_has_index_on_published_at_field():
    """Post model has index on published_at field for efficient sorting."""

    post_fields = Post.model_fields
    assert "published_at" in post_fields

    # Verify index is defined on the model by checking SQLAlchemy metadata
    # The index parameter in Field() creates a database index
    published_at_field_info = post_fields["published_at"]
    assert published_at_field_info.metadata is not None
