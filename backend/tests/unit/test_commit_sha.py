"""Unit tests for CommitSHA value object."""

import pytest

from backend.domain.value_objects.commit_sha import CommitSHA


class TestCommitSHAValidation:
    """Test valid commit SHA acceptance and normalization."""

    def test_commit_sha_accepts_valid_40_char_hex(self) -> None:
        """CommitSHA accepts a valid 40-character hexadecimal string."""
        valid_sha = "a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0"
        commit_sha = CommitSHA(valid_sha)
        assert str(commit_sha) == valid_sha

    def test_commit_sha_uppercase_normalized_to_lowercase(self) -> None:
        """CommitSHA normalizes uppercase hex characters to lowercase."""
        uppercase_sha = "A1B2C3D4E5F6A7B8C9D0E1F2A3B4C5D6E7F8A9B0"
        commit_sha = CommitSHA(uppercase_sha)
        assert str(commit_sha) == uppercase_sha.lower()

    def test_commit_sha_stores_value_correctly(self) -> None:
        """str(commit_sha) returns the full 40-character SHA."""
        sha_value = "1234567890abcdef1234567890abcdef12345678"
        commit_sha = CommitSHA(sha_value)
        assert str(commit_sha) == sha_value


class TestCommitSHAShortGeneration:
    """Test short SHA generation from full commit hash."""

    def test_commit_sha_short_returns_first_7_chars(self) -> None:
        """short_sha property returns the first 7 characters of the full SHA."""
        full_sha = "abcdef1234567890abcdef1234567890abcdef12"
        commit_sha = CommitSHA(full_sha)
        assert commit_sha.short_sha == "abcdef1"

    def test_commit_sha_short_is_lowercase(self) -> None:
        """short_sha is normalized to lowercase even when input is uppercase."""
        uppercase_sha = "ABCDEF1234567890ABCDEF1234567890ABCDEF12"
        commit_sha = CommitSHA(uppercase_sha)
        assert commit_sha.short_sha == "abcdef1"


class TestCommitSHAValidationErrors:
    """Test validation error cases for invalid commit SHAs."""

    def test_commit_sha_rejects_none(self) -> None:
        """CommitSHA raises TypeError when initialized with None."""
        with pytest.raises(TypeError):
            CommitSHA(None)  # type: ignore[arg-type]

    def test_commit_sha_rejects_empty_string(self) -> None:
        """CommitSHA raises ValueError when initialized with empty string."""
        with pytest.raises(ValueError, match="Commit SHA cannot be empty"):
            CommitSHA("")

    def test_commit_sha_rejects_non_hex_characters(self) -> None:
        """CommitSHA raises ValueError when SHA contains non-hexadecimal characters."""
        invalid_sha = "g1h2i3j4k5l6m7n8o9p0q1r2s3t4u5v6w7x8y9z0"
        with pytest.raises(
            ValueError, match="Commit SHA must contain only hexadecimal characters"
        ):
            CommitSHA(invalid_sha)

    def test_commit_sha_rejects_wrong_length(self) -> None:
        """CommitSHA raises ValueError when SHA is not exactly 40 characters."""
        short_sha = "abc123"
        with pytest.raises(
            ValueError, match="Commit SHA must be exactly 40 characters"
        ):
            CommitSHA(short_sha)

    def test_commit_sha_rejects_short_sha(self) -> None:
        """CommitSHA rejects 7-character short SHAs."""
        short_sha = "abcdef1"
        with pytest.raises(
            ValueError, match="Commit SHA must be exactly 40 characters"
        ):
            CommitSHA(short_sha)


class TestCommitSHAImmutability:
    """Test immutability and equality behavior of CommitSHA."""

    def test_commit_sha_is_immutable(self) -> None:
        """CommitSHA value cannot be modified after creation."""
        sha_value = "a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0"
        commit_sha = CommitSHA(sha_value)
        with pytest.raises(AttributeError):
            commit_sha.value = "different_sha_value"  # type: ignore[misc]

    def test_commit_sha_equality_by_value(self) -> None:
        """Two CommitSHA instances with the same value are equal."""
        sha_value = "a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0"
        commit_sha1 = CommitSHA(sha_value)
        commit_sha2 = CommitSHA(sha_value)
        assert commit_sha1 == commit_sha2
