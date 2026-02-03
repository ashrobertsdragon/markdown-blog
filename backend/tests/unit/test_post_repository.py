"""Unit tests for PostRepository infrastructure layer.

This module tests the conversion between PostModel (database) and Post
aggregate (domain) to ensure proper handling of renamed fields and timezone
awareness.

Test Coverage:
- Field mapping: html_content vs published_html (2 tests)
- Timezone awareness for published_at (3 tests)
- Conversion between model and domain (2 tests)
"""

from datetime import UTC, datetime
from unittest.mock import Mock

import pytest

from backend.domain.aggregates.post import Post as DomainPost
from backend.domain.value_objects.html_content import HtmlContent
from backend.domain.value_objects.slug import Slug
from backend.infrastructure.persistence.models import Post as PostModel
from backend.infrastructure.persistence.post_repository import PostRepository


@pytest.fixture
def mock_session() -> Mock:
    """Fixture providing mock database session."""
    return Mock()


@pytest.fixture
def domain_post_fixture() -> DomainPost:
    """Fixture providing a domain Post aggregate."""
    return DomainPost(
        id=1,
        slug=Slug("test-post"),
        title="Test Post",
        author_id=1,
        _html_content=HtmlContent("<p>Test content</p>"),
        published=True,
        published_at=datetime(2025, 1, 15, 14, 30, 0, tzinfo=UTC),
        created_at=datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC),
        updated_at=datetime(2025, 1, 15, 14, 30, 0, tzinfo=UTC),
    )


@pytest.fixture
def post_model_fixture() -> PostModel:
    """Fixture providing a PostModel database table instance."""
    return PostModel(
        id=1,
        slug="test-post",
        title="Test Post",
        html_content="<p>Test content</p>",
        published=True,
        published_at=datetime(2025, 1, 15, 14, 30, 0, tzinfo=UTC),
        author_id=1,
        created_at=datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC),
        updated_at=datetime(2025, 1, 15, 14, 30, 0, tzinfo=UTC),
    )


def test_to_model_converts_html_content_to_database_field(
    mock_session: Mock, domain_post_fixture: DomainPost
) -> None:
    """Verify _to_model maps html_content value object to model field.

    The PostRepository should convert domain Post.html_content
    (HtmlContent value object) to PostModel.html_content (string)
    for database persistence.
    """
    repo = PostRepository(session=mock_session)
    model = repo._to_model(domain_post_fixture)

    assert hasattr(model, "html_content")
    assert model.html_content == "<p>Test content</p>"
    assert isinstance(model.html_content, str)


def test_to_domain_converts_html_content_from_database_field(
    mock_session: Mock, post_model_fixture: PostModel
) -> None:
    """Verify _to_domain maps model html_content to domain value object.

    The PostRepository should convert PostModel.html_content (string)
    to domain Post.html_content (HtmlContent value object) when
    loading from database.
    """
    repo = PostRepository(session=mock_session)
    domain_post = repo._to_domain(post_model_fixture)

    assert domain_post.html_content is not None
    assert isinstance(domain_post.html_content, HtmlContent)
    assert domain_post.html_content.value == "<p>Test content</p>"


def test_to_domain_handles_naive_datetime_for_published_at(
    mock_session: Mock,
) -> None:
    """Verify _to_domain adds UTC timezone to naive published_at datetime.

    When PostModel.published_at lacks timezone info (naive datetime),
    the repository should add UTC timezone to maintain consistency with
    domain Post expectations.
    """
    naive_published_at = datetime(2025, 1, 15, 14, 30, 0)
    post_model = PostModel(
        id=1,
        slug="test-post",
        title="Test Post",
        html_content="<p>Content</p>",
        published=True,
        published_at=naive_published_at,
        author_id=1,
        created_at=datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC),
        updated_at=datetime(2025, 1, 15, 14, 30, 0, tzinfo=UTC),
    )

    repo = PostRepository(session=mock_session)
    domain_post = repo._to_domain(post_model)

    assert domain_post.published_at is not None
    assert domain_post.published_at.tzinfo is not None
    assert domain_post.published_at.tzinfo == UTC
    assert domain_post.published_at == naive_published_at.replace(tzinfo=UTC)


def test_to_domain_preserves_timezone_aware_published_at(
    mock_session: Mock,
) -> None:
    """Verify _to_domain preserves existing timezone for published_at.

    When PostModel.published_at already has timezone info, the repository
    should preserve it without modification.
    """
    aware_published_at = datetime(2025, 1, 15, 14, 30, 0, tzinfo=UTC)
    post_model = PostModel(
        id=1,
        slug="test-post",
        title="Test Post",
        html_content="<p>Content</p>",
        published=True,
        published_at=aware_published_at,
        author_id=1,
        created_at=datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC),
        updated_at=datetime(2025, 1, 15, 14, 30, 0, tzinfo=UTC),
    )

    repo = PostRepository(session=mock_session)
    domain_post = repo._to_domain(post_model)

    assert domain_post.published_at == aware_published_at
    assert domain_post.published_at.tzinfo == UTC


def test_to_domain_handles_none_published_at(mock_session: Mock) -> None:
    """Verify _to_domain correctly handles None for published_at.

    When PostModel.published_at is None (draft post), the repository
    should set domain Post.published_at to None without attempting
    timezone conversion.
    """
    post_model = PostModel(
        id=1,
        slug="test-draft",
        title="Test Draft",
        html_content="",
        published=False,
        published_at=None,
        author_id=1,
        created_at=datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC),
        updated_at=datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC),
    )

    repo = PostRepository(session=mock_session)
    domain_post = repo._to_domain(post_model)

    assert domain_post.published_at is None


def test_to_model_preserves_published_at_from_domain(
    mock_session: Mock,
) -> None:
    """Verify _to_model preserves published_at timestamp from domain.

    When converting domain Post to PostModel, the repository should
    preserve the published_at timestamp exactly as it appears in the
    domain aggregate.
    """
    published_at = datetime(2025, 1, 15, 14, 30, 0, tzinfo=UTC)
    domain_post = DomainPost(
        id=1,
        slug=Slug("test-post"),
        title="Test Post",
        author_id=1,
        _html_content=HtmlContent("<p>Content</p>"),
        published=True,
        published_at=published_at,
        created_at=datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC),
        updated_at=datetime(2025, 1, 15, 14, 30, 0, tzinfo=UTC),
    )

    repo = PostRepository(session=mock_session)
    model = repo._to_model(domain_post)

    assert model.published_at == published_at


def test_to_model_handles_none_html_content(mock_session: Mock) -> None:
    """Verify _to_model converts None html_content to empty string.

    When domain Post.html_content is None (unpublished draft), the
    repository should convert it to empty string for database storage
    rather than storing NULL.
    """
    domain_post = DomainPost(
        id=1,
        slug=Slug("test-draft"),
        title="Test Draft",
        author_id=1,
        _html_content=None,
        published=False,
        published_at=None,
        created_at=datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC),
        updated_at=datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC),
    )

    repo = PostRepository(session=mock_session)
    model = repo._to_model(domain_post)

    assert model.html_content == ""
    assert isinstance(model.html_content, str)
