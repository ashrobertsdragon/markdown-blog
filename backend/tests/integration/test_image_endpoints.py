"""Integration tests for the images API blueprint.

Tests POST /api/posts/<slug>/images, GET /api/posts/<slug>/images, and
DELETE /api/posts/<slug>/images/<filename> using a minimal Flask test app
with images_bp registered directly (independent of main.py registration).
"""

from datetime import UTC, datetime
from io import BytesIO
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from flask import Flask, jsonify
from flask.testing import FlaskClient

from backend.api.routes.images import images_bp
from backend.domain.aggregates.user import User
from backend.domain.value_objects.role import Role
from backend.exceptions import AuthenticationError

JPEG_BYTES = b"\xff\xd8\xff\xe0" + b"\x00" * 20
PNG_BYTES = b"\x89PNG\r\n\x1a\n" + b"\x00" * 20
WEBP_BYTES = b"RIFF\x00\x00\x00\x00WEBP" + b"\x00" * 20


@pytest.fixture
def uploads_dir(tmp_path: Path) -> Path:
    """Return a fresh uploads directory for each test."""
    path = tmp_path / "uploads"
    path.mkdir()
    return path


@pytest.fixture
def author_user() -> User:
    """Return a User with AUTHOR role who owns the test post."""
    return User(
        id=1,
        clerk_user_id="clerk_author_123",
        email="author@example.com",
        role=Role.AUTHOR,
        created_at=datetime(2024, 1, 1, 12, 0, 0, tzinfo=UTC),
    )


@pytest.fixture
def other_user() -> User:
    """Return a User with AUTHOR role who does NOT own the test post."""
    return User(
        id=2,
        clerk_user_id="clerk_other_456",
        email="other@example.com",
        role=Role.AUTHOR,
        created_at=datetime(2024, 1, 1, 12, 0, 0, tzinfo=UTC),
    )


@pytest.fixture
def test_post() -> MagicMock:
    """Return a mock Post with author_id=1."""
    post = MagicMock()
    post.author_id = 1
    return post


@pytest.fixture
def app(uploads_dir: Path, monkeypatch: pytest.MonkeyPatch) -> Flask:
    """Minimal Flask app with images_bp and a fresh UPLOADS_PATH."""
    monkeypatch.setenv("UPLOADS_PATH", str(uploads_dir))
    import backend.api.routes.images as images_module

    monkeypatch.setattr(images_module, "_filesystem_settings", None)
    flask_app = Flask(__name__)
    flask_app.register_blueprint(images_bp, url_prefix="/api/posts")
    flask_app.config["TESTING"] = True

    @flask_app.errorhandler(AuthenticationError)
    def handle_auth_error(error: AuthenticationError) -> tuple[Any, int]:
        """Map AuthenticationError to 401 JSON response."""
        return jsonify({"error": str(error)}), 401

    return flask_app


@pytest.fixture
def client(app: Flask) -> FlaskClient:
    """Return a test client for the images app."""
    return app.test_client()


def _auth_patches(user: User) -> tuple[MagicMock, MagicMock]:
    """Return (mock_clerk_adapter, mock_user_repo) pre-configured for user."""
    mock_clerk = MagicMock()
    mock_clerk.verify_token.return_value = {
        "sub": user.clerk_user_id,
        "email": user.email,
    }
    mock_user_repo = MagicMock()
    mock_user_repo.find_by_clerk_user_id.return_value = user
    return mock_clerk, mock_user_repo


def _upload(
    client: FlaskClient,
    slug: str,
    data: bytes,
    filename: str,
    **kwargs: Any,
) -> Any:
    """POST a multipart file upload to /api/posts/<slug>/images."""
    return client.post(
        f"/api/posts/{slug}/images",
        data={"file": (BytesIO(data), filename)},
        content_type="multipart/form-data",
        **kwargs,
    )


def test_upload_image_returns_201_for_valid_jpeg(
    client: FlaskClient,
    author_user: User,
    test_post: MagicMock,
    uploads_dir: Path,
) -> None:
    """Valid JPEG upload by the post owner should return 201 with a URL."""
    mock_clerk, mock_user_repo = _auth_patches(author_user)
    mock_post_repo = MagicMock()
    mock_post_repo.find_by_slug.return_value = test_post

    with (
        patch(
            "backend.api.middleware.auth_middleware._get_clerk_adapter",
            return_value=mock_clerk,
        ),
        patch(
            "backend.api.middleware.auth_middleware._get_user_repository",
            return_value=mock_user_repo,
        ),
        patch(
            "backend.api.routes.images._get_post_repository",
            return_value=mock_post_repo,
        ),
    ):
        response = _upload(
            client,
            "my-post",
            JPEG_BYTES,
            "photo.jpg",
            headers={"Authorization": "Bearer valid_token"},
        )

    assert response.status_code == 201
    body = response.get_json()
    assert "url" in body
    assert body["url"].startswith("/uploads/my-post/")
    assert body["url"].endswith(".jpg")
    assert (uploads_dir / "my-post").is_dir()


def test_upload_image_returns_413_when_file_exceeds_max_upload_size(
    client: FlaskClient,
    author_user: User,
    test_post: MagicMock,
) -> None:
    """Body larger than MAX_UPLOAD_SIZE (5 MB) should return 413."""
    large_jpeg = b"\xff\xd8\xff\xe0" + b"\x00" * (5 * 1024 * 1024 + 1)
    mock_clerk, mock_user_repo = _auth_patches(author_user)
    mock_post_repo = MagicMock()
    mock_post_repo.find_by_slug.return_value = test_post

    with (
        patch(
            "backend.api.middleware.auth_middleware._get_clerk_adapter",
            return_value=mock_clerk,
        ),
        patch(
            "backend.api.middleware.auth_middleware._get_user_repository",
            return_value=mock_user_repo,
        ),
        patch(
            "backend.api.routes.images._get_post_repository",
            return_value=mock_post_repo,
        ),
    ):
        response = _upload(
            client,
            "my-post",
            large_jpeg,
            "big.jpg",
            headers={"Authorization": "Bearer valid_token"},
        )

    assert response.status_code == 413


def test_upload_image_returns_400_for_unsupported_extension(
    client: FlaskClient,
    author_user: User,
    test_post: MagicMock,
) -> None:
    """File with unsupported extension (.exe) should return 400."""
    mock_clerk, mock_user_repo = _auth_patches(author_user)
    mock_post_repo = MagicMock()
    mock_post_repo.find_by_slug.return_value = test_post

    with (
        patch(
            "backend.api.middleware.auth_middleware._get_clerk_adapter",
            return_value=mock_clerk,
        ),
        patch(
            "backend.api.middleware.auth_middleware._get_user_repository",
            return_value=mock_user_repo,
        ),
        patch(
            "backend.api.routes.images._get_post_repository",
            return_value=mock_post_repo,
        ),
    ):
        response = _upload(
            client,
            "my-post",
            b"MZ\x90\x00",
            "malware.exe",
            headers={"Authorization": "Bearer valid_token"},
        )

    assert response.status_code == 400


def test_upload_image_returns_400_for_magic_bytes_mismatch(
    client: FlaskClient,
    author_user: User,
    test_post: MagicMock,
) -> None:
    """PNG bytes with .jpg extension should return 400 (magic-byte mismatch)."""
    mock_clerk, mock_user_repo = _auth_patches(author_user)
    mock_post_repo = MagicMock()
    mock_post_repo.find_by_slug.return_value = test_post

    with (
        patch(
            "backend.api.middleware.auth_middleware._get_clerk_adapter",
            return_value=mock_clerk,
        ),
        patch(
            "backend.api.middleware.auth_middleware._get_user_repository",
            return_value=mock_user_repo,
        ),
        patch(
            "backend.api.routes.images._get_post_repository",
            return_value=mock_post_repo,
        ),
    ):
        response = _upload(
            client,
            "my-post",
            PNG_BYTES,
            "disguised.jpg",
            headers={"Authorization": "Bearer valid_token"},
        )

    assert response.status_code == 400
    assert "content" in response.get_json()["error"].lower()


def test_upload_image_returns_401_without_authorization_header(
    client: FlaskClient,
) -> None:
    """Request without Authorization header should return 401.

    require_auth initialises its adapters before checking the header, so
    _get_clerk_adapter and _get_user_repository must be patched even though
    they are never actually called on this code path.
    """
    mock_clerk = MagicMock()
    mock_user_repo = MagicMock()

    with (
        patch(
            "backend.api.middleware.auth_middleware._get_clerk_adapter",
            return_value=mock_clerk,
        ),
        patch(
            "backend.api.middleware.auth_middleware._get_user_repository",
            return_value=mock_user_repo,
        ),
    ):
        response = _upload(client, "my-post", JPEG_BYTES, "photo.jpg")

    assert response.status_code == 401


def test_upload_image_returns_403_for_wrong_author(
    client: FlaskClient,
    other_user: User,
    test_post: MagicMock,
) -> None:
    """User who does not own the post should receive 403."""
    mock_clerk, mock_user_repo = _auth_patches(other_user)
    mock_post_repo = MagicMock()
    mock_post_repo.find_by_slug.return_value = test_post

    with (
        patch(
            "backend.api.middleware.auth_middleware._get_clerk_adapter",
            return_value=mock_clerk,
        ),
        patch(
            "backend.api.middleware.auth_middleware._get_user_repository",
            return_value=mock_user_repo,
        ),
        patch(
            "backend.api.routes.images._get_post_repository",
            return_value=mock_post_repo,
        ),
    ):
        response = _upload(
            client,
            "my-post",
            JPEG_BYTES,
            "photo.jpg",
            headers={"Authorization": "Bearer valid_token"},
        )

    assert response.status_code == 403


def test_list_images_returns_200_with_uploaded_urls(
    client: FlaskClient,
    author_user: User,
    test_post: MagicMock,
    uploads_dir: Path,
) -> None:
    """GET images for a post returns 200 with sorted URL list."""
    slug_dir = uploads_dir / "my-post"
    slug_dir.mkdir()
    (slug_dir / "photo.jpg").write_bytes(JPEG_BYTES)

    mock_clerk, mock_user_repo = _auth_patches(author_user)
    mock_post_repo = MagicMock()
    mock_post_repo.find_by_slug.return_value = test_post

    with (
        patch(
            "backend.api.middleware.auth_middleware._get_clerk_adapter",
            return_value=mock_clerk,
        ),
        patch(
            "backend.api.middleware.auth_middleware._get_user_repository",
            return_value=mock_user_repo,
        ),
        patch(
            "backend.api.routes.images._get_post_repository",
            return_value=mock_post_repo,
        ),
    ):
        response = client.get(
            "/api/posts/my-post/images",
            headers={"Authorization": "Bearer valid_token"},
        )

    assert response.status_code == 200
    body = response.get_json()
    assert "images" in body
    assert "/uploads/my-post/photo.jpg" in body["images"]


def test_delete_image_returns_204_for_existing_file(
    client: FlaskClient,
    author_user: User,
    test_post: MagicMock,
    uploads_dir: Path,
) -> None:
    """DELETE an existing image should return 204 and remove the file."""
    slug_dir = uploads_dir / "my-post"
    slug_dir.mkdir()
    (slug_dir / "photo.jpg").write_bytes(JPEG_BYTES)

    mock_clerk, mock_user_repo = _auth_patches(author_user)
    mock_post_repo = MagicMock()
    mock_post_repo.find_by_slug.return_value = test_post

    with (
        patch(
            "backend.api.middleware.auth_middleware._get_clerk_adapter",
            return_value=mock_clerk,
        ),
        patch(
            "backend.api.middleware.auth_middleware._get_user_repository",
            return_value=mock_user_repo,
        ),
        patch(
            "backend.api.routes.images._get_post_repository",
            return_value=mock_post_repo,
        ),
    ):
        response = client.delete(
            "/api/posts/my-post/images/photo.jpg",
            headers={"Authorization": "Bearer valid_token"},
        )

    assert response.status_code == 204
    assert not (slug_dir / "photo.jpg").exists()


def test_delete_image_returns_404_for_missing_file(
    client: FlaskClient,
    author_user: User,
    test_post: MagicMock,
) -> None:
    """DELETE a non-existent image should return 404."""
    mock_clerk, mock_user_repo = _auth_patches(author_user)
    mock_post_repo = MagicMock()
    mock_post_repo.find_by_slug.return_value = test_post

    with (
        patch(
            "backend.api.middleware.auth_middleware._get_clerk_adapter",
            return_value=mock_clerk,
        ),
        patch(
            "backend.api.middleware.auth_middleware._get_user_repository",
            return_value=mock_user_repo,
        ),
        patch(
            "backend.api.routes.images._get_post_repository",
            return_value=mock_post_repo,
        ),
    ):
        response = client.delete(
            "/api/posts/my-post/images/ghost.jpg",
            headers={"Authorization": "Bearer valid_token"},
        )

    assert response.status_code == 404


def test_delete_image_returns_400_for_invalid_filename(
    client: FlaskClient,
    author_user: User,
    test_post: MagicMock,
) -> None:
    """DELETE with a filename that fails ImageFilename validation returns 400."""
    mock_clerk, mock_user_repo = _auth_patches(author_user)
    mock_post_repo = MagicMock()
    mock_post_repo.find_by_slug.return_value = test_post

    with (
        patch(
            "backend.api.middleware.auth_middleware._get_clerk_adapter",
            return_value=mock_clerk,
        ),
        patch(
            "backend.api.middleware.auth_middleware._get_user_repository",
            return_value=mock_user_repo,
        ),
        patch(
            "backend.api.routes.images._get_post_repository",
            return_value=mock_post_repo,
        ),
    ):
        response = client.delete(
            "/api/posts/my-post/images/script.exe",
            headers={"Authorization": "Bearer valid_token"},
        )

    assert response.status_code == 400
