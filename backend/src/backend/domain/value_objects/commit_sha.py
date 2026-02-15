"""CommitSHA value object for Git commit identifiers.

This module provides the CommitSHA value object which validates and normalizes
Git SHA-1 commit hashes to ensure they conform to the 40-character hexadecimal
format required by Git.
"""

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class CommitSHA:
    """Git commit SHA-1 hash value object.

    Represents a GitHub commit SHA, immutable and validated. Commit SHAs are
    normalized to lowercase and validated to ensure they are exactly 40
    hexadecimal characters.

    Attributes:
        value: 40-character hex string (lowercase)

    Raises:
        TypeError: If raw_sha is None.
        ValueError: If SHA is empty, not exactly 40 characters, or contains
            non-hexadecimal characters.

    Examples:
        >>> sha = CommitSHA("a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0")
        >>> str(sha)
        'a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0'

        >>> sha.short_sha
        'a1b2c3d'

        >>> CommitSHA("ABCDEF123")
        Traceback (most recent call last):
        ...
        ValueError: Commit SHA must be exactly 40 characters
    """

    value: str

    def __init__(self, raw_sha: str) -> None:
        """Validate and store commit SHA.

        Args:
            raw_sha: 40-character hex string (case-insensitive)

        Raises:
            TypeError: If raw_sha is None
            ValueError: If not valid hex or wrong length
        """
        if raw_sha is None:
            raise TypeError("Commit SHA cannot be None")

        if not raw_sha:
            raise ValueError("Commit SHA cannot be empty")

        normalized = raw_sha.lower()

        if len(normalized) != 40:
            raise ValueError("Commit SHA must be exactly 40 characters")

        if not re.match(r"^[a-f0-9]{40}$", normalized):
            raise ValueError(
                "Commit SHA must contain only hexadecimal characters"
            )

        object.__setattr__(self, "value", normalized)

    @property
    def short_sha(self) -> str:
        """Return first 7 characters for UI display.

        Returns:
            First 7 characters of the commit SHA.
        """
        return self.value[:7]

    def __str__(self) -> str:
        """Return full commit SHA.

        Returns:
            The complete 40-character commit SHA.
        """
        return self.value
