"""Images API blueprint for post image management.

Provides upload, list, and delete endpoints under /api/posts/<slug>/images.
Part of the Content Management bounded context HTTP layer.
"""

import logging
from typing import Any

from flask import Blueprint, Response, g, jsonify, request

from backend.api.middleware.auth_middleware import require_auth
from backend.config import FileSystemSettings
from backend.domain.value_objects.image_filename import ImageFilename
from backend.infrastructure.persistence.image_repository import (
    FileSystemImageRepository,
)
from backend.infrastructure.persistence.post_repository import PostRepository

images_bp = Blueprint("images", __name__)
logger = logging.getLogger(__name__)

MAGIC_SIGNATURES: dict[str, list[bytes]] = {
    ".jpg": [b"\xff\xd8\xff"],
    ".jpeg": [b"\xff\xd8\xff"],
    ".png": [b"\x89PNG\r\n\x1a\n"],
    ".gif": [b"GIF87a", b"GIF89a"],
}

_filesystem_settings: FileSystemSettings | None = None


def _get_filesystem_settings() -> FileSystemSettings:
    """Lazily initialise FileSystemSettings."""
    global _filesystem_settings
    if _filesystem_settings is None:
        _filesystem_settings = FileSystemSettings()
    return _filesystem_settings


def _get_image_repository() -> FileSystemImageRepository:
    """Return a FileSystemImageRepository for the configured uploads path."""
    return FileSystemImageRepository(_get_filesystem_settings().UPLOADS_PATH)


def _get_post_repository() -> PostRepository:
    """Return a PostRepository instance."""
    return PostRepository()


def _is_valid_magic(data: bytes, extension: str) -> bool:
    """Return True when leading bytes match the extension's magic signature.

    WebP is handled separately because its identifier spans two
    non-contiguous byte ranges (bytes 0–4 and 8–12).
    """
    if extension == ".webp":
        return len(data) >= 12 and data[:4] == b"RIFF" and data[8:12] == b"WEBP"
    return any(
        data[: len(sig)] == sig for sig in MAGIC_SIGNATURES.get(extension, [])
    )


def _owns_post(post: Any) -> bool:
    """Return True if the current user owns the post or is an admin."""
    is_owner: bool = post.author_id == g.current_user.id
    is_admin: bool = g.current_user.role.value == "admin"
    return is_owner or is_admin


@images_bp.route("/<slug>/images", methods=["POST"])
@require_auth
def upload_image(slug: str) -> tuple[Response, int]:
    """Upload an image for a post.

    Validates Content-Length against MAX_UPLOAD_SIZE before reading the body,
    then checks post ownership, file extension, and magic bytes before saving.

    Args:
        slug: Post slug identifying the target post.

    Returns:
        201 with ``{"url": "<public path>"}`` on success.

    Raises:
        400: Missing file, unsupported extension, or magic-byte mismatch.
        401: Missing or invalid authentication.
        403: Authenticated user does not own the post.
        404: Post not found.
        413: Content-Length or actual body exceeds MAX_UPLOAD_SIZE.
    """
    fs = _get_filesystem_settings()
    content_length = request.content_length
    if content_length is not None and content_length > fs.MAX_UPLOAD_SIZE:
        return jsonify({"error": "File too large"}), 413

    post = _get_post_repository().find_by_slug(slug)
    if post is None:
        return jsonify({"error": "Post not found"}), 404

    if not _owns_post(post):
        return jsonify({"error": "Forbidden"}), 403

    if "file" not in request.files:
        return jsonify({"error": "No file provided"}), 400

    file = request.files["file"]
    try:
        image_filename = ImageFilename(file.filename or "")
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400

    data = file.read()
    if len(data) > fs.MAX_UPLOAD_SIZE:
        return jsonify({"error": "File too large"}), 413

    if not _is_valid_magic(data, image_filename.extension):
        return jsonify({"error": "File content does not match extension"}), 400

    url = _get_image_repository().save(slug, image_filename.value, data)
    logger.info(
        "Image uploaded",
        extra={"slug": slug, "filename": image_filename.value},
    )
    return jsonify({"url": url}), 201


@images_bp.route("/<slug>/images", methods=["GET"])
@require_auth
def list_images(slug: str) -> tuple[Response, int]:
    """List all images uploaded for a post.

    Args:
        slug: Post slug identifying the target post.

    Returns:
        200 with ``{"images": ["/uploads/<slug>/<filename>", ...]}``.

    Raises:
        401: Missing or invalid authentication.
        403: Authenticated user does not own the post.
        404: Post not found.
    """
    post = _get_post_repository().find_by_slug(slug)
    if post is None:
        return jsonify({"error": "Post not found"}), 404

    if not _owns_post(post):
        return jsonify({"error": "Forbidden"}), 403

    images = _get_image_repository().list_by_post(slug)
    return jsonify({"images": images}), 200


@images_bp.route("/<slug>/images/<filename>", methods=["DELETE"])
@require_auth
def delete_image(slug: str, filename: str) -> Response | tuple[Response, int]:
    """Delete an uploaded image.

    Args:
        slug: Post slug the image belongs to.
        filename: Filename of the image to remove.

    Returns:
        204 No Content on success.

    Raises:
        401: Missing or invalid authentication.
        403: Authenticated user does not own the post.
        404: Post not found or image file does not exist.
    """
    post = _get_post_repository().find_by_slug(slug)
    if post is None:
        return jsonify({"error": "Post not found"}), 404

    if not _owns_post(post):
        return jsonify({"error": "Forbidden"}), 403

    try:
        _get_image_repository().delete(slug, filename)
    except FileNotFoundError:
        return jsonify({"error": "Image not found"}), 404

    return Response(status=204)
