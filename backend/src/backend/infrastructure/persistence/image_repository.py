"""Filesystem-based image repository implementation.

Stores uploaded images under ``uploads/{slug}/{filename}`` and provides
URL paths suitable for use in ``<img src>`` attributes and API responses.
Part of the Content Management bounded context infrastructure layer.
"""

from pathlib import Path


class FileSystemImageRepository:
    """Repository for managing uploaded image files on the filesystem.

    Images are stored at ``{uploads_path}/{slug}/{filename}``.
    The slug subdirectory is created on first use if absent.

    Attributes:
        uploads_path: Root directory under which per-slug subdirectories live.
    """

    def __init__(self, uploads_path: Path) -> None:
        """Initialise the repository.

        Args:
            uploads_path: Root uploads directory. Created if absent.
        """
        self.uploads_path = Path(uploads_path)
        self.uploads_path.mkdir(exist_ok=True, parents=True)

    def save(self, slug: str, filename: str, data: bytes) -> str:
        """Persist image bytes and return the public URL path.

        Args:
            slug: Post slug used as the subdirectory name.
            filename: Sanitized image filename (e.g. ``"photo.jpg"``).
            data: Raw image bytes to write.

        Returns:
            Public URL path of the form ``/uploads/{slug}/{filename}``.
        """
        slug_dir = self.uploads_path / slug
        slug_dir.mkdir(exist_ok=True, parents=True)
        (slug_dir / filename).write_bytes(data)
        return f"/uploads/{slug}/{filename}"

    def list_by_post(self, slug: str) -> list[str]:
        """Return sorted URL paths for all images uploaded to a post.

        Args:
            slug: Post slug whose images to list.

        Returns:
            Sorted list of ``/uploads/{slug}/{filename}`` strings,
            or an empty list if no images exist for the slug.
        """
        slug_dir = self.uploads_path / slug
        if not slug_dir.exists():
            return []
        return sorted(
            f"/uploads/{slug}/{p.name}"
            for p in slug_dir.iterdir()
            if p.is_file()
        )

    def delete(self, slug: str, filename: str) -> None:
        """Delete an uploaded image file.

        Args:
            slug: Post slug the image belongs to.
            filename: Filename of the image to remove.

        Raises:
            FileNotFoundError: If the file does not exist.
        """
        target = self.uploads_path / slug / filename
        if not target.exists():
            raise FileNotFoundError(
                f"Image not found: uploads/{slug}/{filename}"
            )
        target.unlink()
