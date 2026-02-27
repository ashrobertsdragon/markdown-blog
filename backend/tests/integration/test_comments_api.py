"""Integration tests for the comments API endpoints.

Documents the expected HTTP contract for comment submission. These tests
require the Flask comment routes defined in Task 5.
"""

import pytest


@pytest.mark.skip(reason="requires Task 5: comment API routes")
def test_post_comment_returns_201_created() -> None:
    """POST /api/posts/{slug}/comments returns 201 with comment data."""
    ...


@pytest.mark.skip(reason="requires Task 5: comment API routes")
def test_rate_limit_returns_429_with_headers() -> None:
    """Rate limit exceeded returns 429 with X-RateLimit-Remaining header."""
    ...


@pytest.mark.skip(reason="requires Task 5: comment API routes")
def test_post_comment_unauthenticated_returns_401() -> None:
    """POST without authentication credentials returns 401."""
    ...


@pytest.mark.skip(reason="requires Task 5: comment API routes")
def test_post_comment_empty_text_returns_400() -> None:
    """POST with empty text body returns 400 with a validation error."""
    ...


@pytest.mark.skip(reason="requires Task 5: comment API routes")
def test_post_comment_unknown_slug_returns_404() -> None:
    """POST to a slug that does not exist returns 404."""
    ...


@pytest.mark.skip(reason="requires Task 5: comment API routes")
def test_spam_comment_returns_201_pending_moderation() -> None:
    """POST with high-spam text returns 201 with is_pending_moderation=true."""
    ...


@pytest.mark.skip(reason="requires Task 5: comment API routes")
def test_list_comments_returns_200_with_array() -> None:
    """GET /api/posts/{slug}/comments returns 200 with a list of comments."""
    ...
