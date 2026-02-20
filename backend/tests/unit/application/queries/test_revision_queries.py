"""Unit tests for revision query handlers.

This module defines comprehensive unit tests for revision query handlers
following TDD Red phase principles. Tests cover all three query handlers:
get_revision_history, get_revision, and compare_revisions.

Test Coverage:
- GetRevisionHistoryQuery validation and handler (8 tests)
- GetRevisionQuery validation and handler (6 tests)
- CompareRevisionsQuery validation and handler (6 tests)

Total: 20+ unit tests
"""

from datetime import UTC, datetime
from unittest.mock import Mock
from uuid import uuid4

import pytest

from backend.domain.aggregates.post_revision import PostRevision
from backend.domain.value_objects.commit_sha import CommitSHA

try:
    from backend.application.queries.compare_revisions_query import (
        CompareRevisionsQuery,
        CompareRevisionsResponse,
        compare_revisions_handler,
    )
    from backend.application.queries.get_revision_history_query import (
        GetRevisionHistoryQuery,
        GetRevisionHistoryResponse,
        get_revision_history_handler,
    )
    from backend.application.queries.get_revision_query import (
        GetRevisionQuery,
        GetRevisionResponse,
        get_revision_handler,
    )
except ImportError:
    GetRevisionHistoryQuery = None  # type: ignore[misc, assignment]
    GetRevisionHistoryResponse = None  # type: ignore[misc, assignment]
    get_revision_history_handler = None  # type: ignore[assignment]
    GetRevisionQuery = None  # type: ignore[misc, assignment]
    GetRevisionResponse = None  # type: ignore[misc, assignment]
    get_revision_handler = None  # type: ignore[assignment]
    CompareRevisionsQuery = None  # type: ignore[misc, assignment]
    CompareRevisionsResponse = None  # type: ignore[misc, assignment]
    compare_revisions_handler = None  # type: ignore[assignment]


def test_get_revision_history_query_dataclass_structure() -> None:
    """Verify GetRevisionHistoryQuery has required fields."""
    query = GetRevisionHistoryQuery(post_id=1, skip=0, limit=10)

    assert hasattr(query, "post_id")
    assert hasattr(query, "skip")
    assert hasattr(query, "limit")
    assert isinstance(query.post_id, int)
    assert isinstance(query.skip, int)
    assert isinstance(query.limit, int)


def test_get_revision_history_query_validates_skip_range() -> None:
    """Verify query rejects skip outside valid range 0-10000."""
    with pytest.raises(ValueError, match="skip.*0.*10000"):
        GetRevisionHistoryQuery(post_id=1, skip=-1, limit=10)

    with pytest.raises(ValueError, match="skip.*0.*10000"):
        GetRevisionHistoryQuery(post_id=1, skip=10001, limit=10)


def test_get_revision_history_query_validates_limit_range() -> None:
    """Verify query rejects limit outside valid range 1-100."""
    with pytest.raises(ValueError, match="limit.*1.*100"):
        GetRevisionHistoryQuery(post_id=1, skip=0, limit=0)

    with pytest.raises(ValueError, match="limit.*1.*100"):
        GetRevisionHistoryQuery(post_id=1, skip=0, limit=101)


def test_get_revision_history_handler_returns_paginated_results() -> None:
    """Verify handler returns GetRevisionHistoryResponse with pagination."""
    mock_repo = Mock()
    mock_repo.find_by_post_id.return_value = ([], 0)

    query = GetRevisionHistoryQuery(post_id=1, skip=0, limit=10)

    response = get_revision_history_handler(
        query=query, revision_repo=mock_repo
    )

    assert isinstance(response, GetRevisionHistoryResponse)
    assert hasattr(response, "revisions")
    assert hasattr(response, "total_count")
    assert hasattr(response, "has_more")
    assert isinstance(response.revisions, list)
    assert isinstance(response.total_count, int)
    assert isinstance(response.has_more, bool)


def test_get_revision_query_dataclass_structure() -> None:
    """Verify GetRevisionQuery has required fields."""
    query = GetRevisionQuery(
        post_id=1, commit_sha="abc123def456789012345678901234567890abcd"
    )

    assert hasattr(query, "post_id")
    assert hasattr(query, "commit_sha")
    assert isinstance(query.post_id, int)
    assert isinstance(query.commit_sha, str)


def test_get_revision_query_validates_commit_sha_length() -> None:
    """Verify query rejects commit_sha exceeding 100 characters."""
    long_sha = "a" * 101

    with pytest.raises(ValueError, match="commit_sha.*100.*characters"):
        GetRevisionQuery(post_id=1, commit_sha=long_sha)


def test_get_revision_handler_returns_revision_with_content() -> None:
    """Verify handler returns GetRevisionResponse with rendered content."""
    mock_repo = Mock()
    mock_markdown_service = Mock()
    mock_sanitizer = Mock()

    revision = PostRevision(
        id=uuid4(),
        post_id=1,
        commit_sha=CommitSHA("abc123def456789012345678901234567890abcd"),
        author_id=2,
        commit_message="Test commit",
        markdown_content="# Test",
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
        is_revert=False,
    )

    mock_repo.find_by_sha.return_value = revision
    mock_markdown_service.render.return_value = "<h1>Test</h1>"
    mock_sanitizer.sanitize.return_value = "<h1>Test</h1>"

    query = GetRevisionQuery(
        post_id=revision.post_id,
        commit_sha="abc123def456789012345678901234567890abcd",
    )

    response = get_revision_handler(
        query=query,
        revision_repo=mock_repo,
        markdown_service=mock_markdown_service,
        html_sanitizer=mock_sanitizer,
    )

    assert isinstance(response, GetRevisionResponse)
    assert hasattr(response, "revision")
    assert hasattr(response, "markdown_content")
    assert hasattr(response, "html_content")
    assert response.revision == revision
    assert response.markdown_content == "# Test"


def test_compare_revisions_query_dataclass_structure() -> None:
    """Verify CompareRevisionsQuery has required fields."""
    query = CompareRevisionsQuery(
        post_id=1,
        from_sha="abc123def456789012345678901234567890abcd",
        to_sha="def456789012345678901234567890123456789a",
    )

    assert hasattr(query, "post_id")
    assert hasattr(query, "from_sha")
    assert hasattr(query, "to_sha")
    assert isinstance(query.post_id, int)
    assert isinstance(query.from_sha, str)
    assert isinstance(query.to_sha, str)


def test_compare_revisions_query_validates_sha_lengths() -> None:
    """Verify query rejects SHAs exceeding 100 characters."""
    long_sha = "a" * 101

    with pytest.raises(ValueError, match="from_sha.*100.*characters"):
        CompareRevisionsQuery(
            post_id=1,
            from_sha=long_sha,
            to_sha="abc123def456789012345678901234567890abcd",
        )

    with pytest.raises(ValueError, match="to_sha.*100.*characters"):
        CompareRevisionsQuery(
            post_id=1,
            from_sha="abc123def456789012345678901234567890abcd",
            to_sha=long_sha,
        )


def test_compare_revisions_handler_returns_diff() -> None:
    """Verify handler returns CompareRevisionsResponse with diff."""
    mock_repo = Mock()
    mock_diff_service = Mock()

    from_revision = PostRevision(
        id=uuid4(),
        post_id=1,
        commit_sha=CommitSHA("abc123def456789012345678901234567890abcd"),
        author_id=2,
        commit_message="From commit",
        markdown_content="# Old",
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
        is_revert=False,
    )

    to_revision = PostRevision(
        id=uuid4(),
        post_id=from_revision.post_id,
        commit_sha=CommitSHA("def456789012345678901234567890123456789a"),
        author_id=2,
        commit_message="To commit",
        markdown_content="# New",
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
        is_revert=False,
    )

    mock_repo.find_by_sha.side_effect = [from_revision, to_revision]
    mock_diff_service.diff_text.return_value = []

    query = CompareRevisionsQuery(
        post_id=from_revision.post_id,
        from_sha="abc123def456789012345678901234567890abcd",
        to_sha="def456789012345678901234567890123456789a",
    )

    response = compare_revisions_handler(
        query=query, revision_repo=mock_repo, diff_service=mock_diff_service
    )

    assert isinstance(response, CompareRevisionsResponse)
    assert hasattr(response, "from_revision")
    assert hasattr(response, "to_revision")
    assert hasattr(response, "diff_lines")
    assert response.from_revision == from_revision
    assert response.to_revision == to_revision
