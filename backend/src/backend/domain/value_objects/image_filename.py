"""ImageFilename value object for validated, sanitized image file names.

This module provides the ImageFilename value object which ensures all uploaded
image filenames have an allowed extension and contain only safe characters,
preventing path traversal and invalid file type attacks at the domain layer.
"""

import re
from dataclasses import dataclass

ALLOWED_EXTENSIONS: frozenset[str] = frozenset(
    {".jpg", ".jpeg", ".png", ".gif", ".webp"}
)


@dataclass(frozen=True)
class ImageFilename:
    """Immutable value object representing a validated image filename.

    Validates that the filename has an allowed image extension and sanitizes
    the stem to contain only alphanumeric characters, hyphens, and underscores.
    The total filename length (stem + extension) must not exceed 100 characters.

    Attributes:
        value: The sanitized full filename (e.g. ``"my_photo-1.jpg"``).
        extension: The lowercase extension including the dot (e.g. ``".jpg"``).

    Raises:
        ValueError: If the filename contains path separators, has an extension
            not in the allowlist, or exceeds 100 characters after sanitization.

    Examples:
        >>> fn = ImageFilename("My Photo.png")
        >>> fn.value
        'MyPhoto.png'
        >>> fn.extension
        '.png'
    """

    value: str
    extension: str

    def __init__(self, raw_filename: str) -> None:
        """Create an ImageFilename with validation and sanitization.

        Args:
            raw_filename: The raw filename string to validate and sanitize.

        Raises:
            ValueError: If the filename contains path separators, has an
                unsupported extension, or exceeds 100 characters.
        """
        if not raw_filename or not raw_filename.strip():
            raise ValueError("Filename cannot be empty")

        if "/" in raw_filename or "\\" in raw_filename or ".." in raw_filename:
            raise ValueError(
                "Filename must not contain path separators or '..' sequences"
            )

        sanitized, ext = self._sanitize(raw_filename)

        object.__setattr__(self, "value", sanitized)
        object.__setattr__(self, "extension", ext)

    def _sanitize(self, raw_filename: str) -> tuple[str, str]:
        """Validate extension and sanitize the filename stem.

        Args:
            raw_filename: The raw filename to process.

        Returns:
            A tuple of (sanitized_full_filename, lowercase_extension).

        Raises:
            ValueError: If the extension is not allowed or the result exceeds
                100 characters.
        """
        dot_index = raw_filename.rfind(".")
        if dot_index <= 0:
            raise ValueError(
                f"Filename must have a supported extension: "
                f"{sorted(ALLOWED_EXTENSIONS)}"
            )

        stem = raw_filename[:dot_index]
        ext = raw_filename[dot_index:].lower()

        if ext not in ALLOWED_EXTENSIONS:
            raise ValueError(
                f"Unsupported extension '{ext}'. "
                f"Allowed: {sorted(ALLOWED_EXTENSIONS)}"
            )

        clean_stem = re.sub(r"[^a-zA-Z0-9_\-]", "", stem)

        result = clean_stem + ext
        if len(result) > 100:
            raise ValueError(
                f"Sanitized filename must not exceed 100 characters, "
                f"got {len(result)}"
            )

        return result, ext

    def __str__(self) -> str:
        """Return the sanitized filename value.

        Returns:
            The sanitized full filename string.
        """
        return self.value
