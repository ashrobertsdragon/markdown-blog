"""Shared fixtures for acceptance tests in the comments suite.

Provides user fixtures for reader, author, and admin roles, along with
corresponding JWT payload stubs and mock_clerk_auth variants that patch
the auth middleware to return each user type.

Also provides a ``published_post`` fixture that inserts a real post row
into the in-memory SQLite test database so comment endpoints have a
target to POST against.

The ``auth_context`` fixture supplies a reusable callable context manager
for switching the active auth user mid-test without duplicating patch
boilerplate.
"""

from collections.abc import Callable, Generator
from contextlib import AbstractContextManager, contextmanager
from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

import pytest

from backend.domain.aggregates.user import User
from backend.domain.value_objects.role import Role


@pytest.fixture
def auth_context() -> Callable[
    [User, dict[str, object]], AbstractContextManager[None]
]:
    """Return a context manager that patches auth middleware for a given user.

    Eliminates the boilerplate of constructing and patching mock Clerk adapter
    and user repository instances directly inside tests. Callers switch the
    active auth identity by entering the returned context manager.

    Returns:
        A callable that accepts a ``User`` and a JWT payload dict and returns
        a context manager that patches both auth middleware singletons for the
        duration of the ``with`` block.
    """

    @contextmanager
    def _auth_context(
        user: User, jwt_payload: dict[str, object]
    ) -> Generator[None]:
        """Patch auth middleware to authenticate as ``user`` for this block.

        Args:
            user: The ``User`` aggregate the middleware should return.
            jwt_payload: The JWT claims dict ``verify_token`` should return.
        """
        mock_adapter = MagicMock()
        mock_adapter.verify_token.return_value = jwt_payload
        mock_repo = MagicMock()
        mock_repo.find_by_clerk_user_id.return_value = user

        with (
            patch(
                "backend.api.middleware.auth_middleware._get_clerk_adapter",
                return_value=mock_adapter,
            ),
            patch(
                "backend.api.middleware.auth_middleware._get_user_repository",
                return_value=mock_repo,
            ),
        ):
            yield

    return _auth_context


@pytest.fixture
def reader_user() -> User:
    """Return an authenticated (reader) user for testing."""
    return User(
        id=20,
        clerk_user_id="clerk_reader_001",
        email="reader@example.com",
        role=Role.AUTHENTICATED,
        created_at=datetime(2024, 1, 1, 12, 0, 0, tzinfo=UTC),
    )


@pytest.fixture
def author_user() -> User:
    """Return an author user for testing."""
    return User(
        id=10,
        clerk_user_id="clerk_author_123",
        email="author@example.com",
        role=Role.AUTHOR,
        created_at=datetime(2024, 1, 1, 12, 0, 0, tzinfo=UTC),
    )


@pytest.fixture
def admin_user() -> User:
    """Return an admin user for testing."""
    return User(
        id=1,
        clerk_user_id="clerk_admin_999",
        email="admin@example.com",
        role=Role.ADMIN,
        created_at=datetime(2024, 1, 1, 12, 0, 0, tzinfo=UTC),
    )


@pytest.fixture
def reader_jwt_payload() -> dict[str, object]:
    """Return a valid JWT payload stub for the reader user."""
    return {
        "sub": "clerk_reader_001",
        "email": "reader@example.com",
        "exp": 9999999999,
    }


@pytest.fixture
def author_jwt_payload() -> dict[str, object]:
    """Return a valid JWT payload stub for the author user."""
    return {
        "sub": "clerk_author_123",
        "email": "author@example.com",
        "exp": 9999999999,
    }


@pytest.fixture
def admin_jwt_payload() -> dict[str, object]:
    """Return a valid JWT payload stub for the admin user."""
    return {
        "sub": "clerk_admin_999",
        "email": "admin@example.com",
        "exp": 9999999999,
    }


@pytest.fixture
def mock_clerk_auth(author_jwt_payload: dict[str, object], author_user: User):
    """Mock Clerk authentication and user repository for author user.

    Maintains backward compatibility with test_post_management.py which
    imports this fixture name and expects author-level access.
    """
    mock_clerk_adapter = MagicMock()
    mock_clerk_adapter.verify_token.return_value = author_jwt_payload

    mock_user_repo = MagicMock()
    mock_user_repo.find_by_clerk_user_id.return_value = author_user

    with (
        patch(
            "backend.api.middleware.auth_middleware._get_clerk_adapter",
            return_value=mock_clerk_adapter,
        ),
        patch(
            "backend.api.middleware.auth_middleware._get_user_repository",
            return_value=mock_user_repo,
        ),
    ):
        yield


@pytest.fixture
def mock_clerk_auth_reader(
    reader_jwt_payload: dict[str, object], reader_user: User
):
    """Mock Clerk authentication and user repository for reader user."""
    mock_clerk_adapter = MagicMock()
    mock_clerk_adapter.verify_token.return_value = reader_jwt_payload

    mock_user_repo = MagicMock()
    mock_user_repo.find_by_clerk_user_id.return_value = reader_user

    with (
        patch(
            "backend.api.middleware.auth_middleware._get_clerk_adapter",
            return_value=mock_clerk_adapter,
        ),
        patch(
            "backend.api.middleware.auth_middleware._get_user_repository",
            return_value=mock_user_repo,
        ),
    ):
        yield


@pytest.fixture
def mock_clerk_auth_admin(
    admin_jwt_payload: dict[str, object], admin_user: User
):
    """Mock Clerk authentication and user repository for admin user."""
    mock_clerk_adapter = MagicMock()
    mock_clerk_adapter.verify_token.return_value = admin_jwt_payload

    mock_user_repo = MagicMock()
    mock_user_repo.find_by_clerk_user_id.return_value = admin_user

    with (
        patch(
            "backend.api.middleware.auth_middleware._get_clerk_adapter",
            return_value=mock_clerk_adapter,
        ),
        patch(
            "backend.api.middleware.auth_middleware._get_user_repository",
            return_value=mock_user_repo,
        ),
    ):
        yield


@pytest.fixture
def published_post(client, mock_clerk_auth):
    """Create and publish a post in the test database via the API.

    Uses the author user (via mock_clerk_auth) to create and publish a
    real post row so that comment endpoints have a valid target slug.

    Returns the slug of the published post.
    """
    slug = "acceptance-test-post"
    client.post(
        "/api/posts",
        headers={"Authorization": "Bearer test-token"},
        json={"slug": slug, "title": "Acceptance Test Post"},
    )
    client.post(
        f"/api/posts/{slug}/publish",
        headers={"Authorization": "Bearer test-token"},
    )
    return slug
