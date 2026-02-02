"""Unit tests for ListPostsQuery dataclass.

This module defines comprehensive unit tests for the ListPostsQuery dataclass
following TDD Red phase principles. These tests will initially fail until
the query is implemented.

Test Coverage:
- Valid query creation with defaults (1 test)
- Valid query with custom values (1 test)
- Invalid page validation (2 tests)
- Invalid limit validation (3 tests)
- Frozen dataclass immutability (1 test)
- Equality comparison (1 test)
- String representation (1 test)

Total: 10 unit tests
"""

import pytest
from backend.application.queries.list_posts_query import (
    ListPostsQuery,
    PostFilter,
)


def test_query_creation_with_defaults() -> None:
    """Verify ListPostsQuery creates with default filter, page, and limit.

    This test ensures the query dataclass provides sensible defaults:
    - filter defaults to PostFilter.ALL (show all posts)
    - page defaults to 1 (first page)
    - limit defaults to 20 (reasonable page size)
    """
    query = ListPostsQuery(author_id=42)

    assert query.author_id == 42
    assert query.filter == PostFilter.ALL
    assert query.page == 1
    assert query.limit == 20


def test_query_creation_with_custom_values() -> None:
    """Verify ListPostsQuery accepts custom filter, page, and limit.

    This test ensures all fields can be customized with valid values:
    - filter can be DRAFTS, PUBLISHED, or ALL
    - page can be any positive integer
    - limit can be 1-100
    """
    query = ListPostsQuery(
        author_id=42, filter=PostFilter.PUBLISHED, page=3, limit=50
    )

    assert query.author_id == 42
    assert query.filter == PostFilter.PUBLISHED
    assert query.page == 3
    assert query.limit == 50


def test_query_filter_drafts_only() -> None:
    """Verify ListPostsQuery accepts DRAFTS filter.

    This test ensures the query can filter for unpublished posts only.
    """
    query = ListPostsQuery(author_id=42, filter=PostFilter.DRAFTS)

    assert query.filter == PostFilter.DRAFTS


def test_query_invalid_page_zero_raises_error() -> None:
    """Verify ListPostsQuery rejects page=0.

    This test ensures pagination validation. Page numbers must be >= 1
    since pagination is 1-indexed. Page 0 should raise ValueError with
    a clear error message.
    """
    with pytest.raises(ValueError, match="page.*must be.*1.*greater"):
        ListPostsQuery(author_id=42, page=0)


def test_query_invalid_page_negative_raises_error() -> None:
    """Verify ListPostsQuery rejects negative page numbers.

    This test ensures pagination validation. Negative page numbers are
    invalid and should raise ValueError with a clear error message.
    """
    with pytest.raises(ValueError, match="page.*must be.*1.*greater"):
        ListPostsQuery(author_id=42, page=-1)


def test_query_invalid_limit_zero_raises_error() -> None:
    """Verify ListPostsQuery rejects limit=0.

    This test ensures limit validation. Limit must be at least 1 since
    requesting zero results doesn't make sense. Should raise ValueError.
    """
    with pytest.raises(ValueError, match="limit.*must be.*between.*1.*100"):
        ListPostsQuery(author_id=42, limit=0)


def test_query_invalid_limit_negative_raises_error() -> None:
    """Verify ListPostsQuery rejects negative limit.

    This test ensures limit validation. Negative limits are invalid and
    should raise ValueError with a clear error message.
    """
    with pytest.raises(ValueError, match="limit.*must be.*between.*1.*100"):
        ListPostsQuery(author_id=42, limit=-1)


def test_query_invalid_limit_exceeds_maximum_raises_error() -> None:
    """Verify ListPostsQuery rejects limit > 100.

    This test ensures limit validation. Limit must not exceed 100 to
    prevent excessive database queries and memory usage. Should raise
    ValueError for limit=101.
    """
    with pytest.raises(ValueError, match="limit.*must be.*between.*1.*100"):
        ListPostsQuery(author_id=42, limit=101)


def test_query_frozen_dataclass_immutability() -> None:
    """Verify ListPostsQuery fields cannot be modified after creation.

    This test ensures the query is immutable using frozen dataclass.
    Attempting to modify any field after construction should raise an
    error, preventing accidental mutation of query objects.
    """
    query = ListPostsQuery(author_id=42)

    with pytest.raises((AttributeError, TypeError)):
        query.author_id = 99  # type: ignore[misc]

    with pytest.raises((AttributeError, TypeError)):
        query.page = 5  # type: ignore[misc]

    with pytest.raises((AttributeError, TypeError)):
        query.limit = 10  # type: ignore[misc]


def test_query_instances_are_comparable() -> None:
    """Verify ListPostsQuery instances can be compared for equality.

    This test ensures dataclass equality works correctly. Two queries
    with identical field values should be equal, while queries with
    different values should not be equal.
    """
    query1 = ListPostsQuery(author_id=42, page=2, limit=10)
    query2 = ListPostsQuery(author_id=42, page=2, limit=10)
    query3 = ListPostsQuery(author_id=42, page=3, limit=10)

    assert query1 == query2
    assert query1 != query3
    assert query2 != query3


def test_query_repr_includes_all_fields() -> None:
    """Verify ListPostsQuery repr includes all field values for debugging.

    This test ensures the string representation shows all query parameters,
    which is useful for debugging and logging. The repr should clearly
    identify the query type and show all field values.
    """
    query = ListPostsQuery(
        author_id=42, filter=PostFilter.PUBLISHED, page=3, limit=50
    )

    repr_str = repr(query)

    assert "ListPostsQuery" in repr_str
    assert "42" in repr_str
    assert "PUBLISHED" in repr_str
    assert "3" in repr_str
    assert "50" in repr_str


def test_query_valid_limit_boundary_values() -> None:
    """Verify ListPostsQuery accepts valid limit boundary values.

    This test ensures the limit validation accepts the minimum (1) and
    maximum (100) valid values without error.
    """
    query_min = ListPostsQuery(author_id=42, limit=1)
    query_max = ListPostsQuery(author_id=42, limit=100)

    assert query_min.limit == 1
    assert query_max.limit == 100


def test_query_invalid_author_id_zero_raises_error() -> None:
    """Verify ListPostsQuery rejects author_id=0.

    This test ensures author_id validation. Author IDs must be positive
    integers since they reference database primary keys. Zero is invalid.
    """
    with pytest.raises(ValueError, match="author_id.*must be.*positive"):
        ListPostsQuery(author_id=0)


def test_query_invalid_author_id_negative_raises_error() -> None:
    """Verify ListPostsQuery rejects negative author_id.

    This test ensures author_id validation. Negative author IDs are
    invalid and should raise ValueError.
    """
    with pytest.raises(ValueError, match="author_id.*must be.*positive"):
        ListPostsQuery(author_id=-1)


def test_post_filter_enum_has_all_values() -> None:
    """Verify PostFilter enum defines DRAFTS, PUBLISHED, and ALL.

    This test ensures the PostFilter enum provides all required filter
    options. The enum should have exactly three members with string values.
    """
    assert hasattr(PostFilter, "DRAFTS")
    assert hasattr(PostFilter, "PUBLISHED")
    assert hasattr(PostFilter, "ALL")

    assert isinstance(PostFilter.DRAFTS.value, str)
    assert isinstance(PostFilter.PUBLISHED.value, str)
    assert isinstance(PostFilter.ALL.value, str)


def test_post_filter_enum_values_are_distinct() -> None:
    """Verify PostFilter enum values are unique.

    This test ensures each filter option has a distinct enum value,
    preventing accidental duplication.
    """
    assert PostFilter.DRAFTS != PostFilter.PUBLISHED
    assert PostFilter.DRAFTS != PostFilter.ALL
    assert PostFilter.PUBLISHED != PostFilter.ALL
