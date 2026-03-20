"""Unit tests for extract_mentions() utility in mention_service.

Covers:
- Extracts a single @username mention
- Extracts multiple distinct @username mentions in order
- Deduplicates repeated mentions (preserves first occurrence order)
- Returns empty list when no mentions present
- Returns empty list for empty string input
"""

from backend.domain.services.mention_service import extract_mentions


class TestExtractMentions:
    """Tests for extract_mentions() utility function."""

    def test_extracts_single_mention(self) -> None:
        """A single @username is returned as a one-element list."""
        result = extract_mentions("Hello @alice")
        assert result == ["alice"]

    def test_extracts_multiple_distinct_mentions(self) -> None:
        """Multiple distinct @usernames are all returned in order."""
        result = extract_mentions("@alice and @bob")
        assert result == ["alice", "bob"]

    def test_deduplicates_repeated_mention(self) -> None:
        """A username mentioned twice appears only once in the result."""
        result = extract_mentions("@alice @alice")
        assert result == ["alice"]

    def test_preserves_order_when_deduplicating(self) -> None:
        """First-seen order is preserved when deduplicating."""
        result = extract_mentions("@bob @alice @bob")
        assert result == ["bob", "alice"]

    def test_returns_empty_list_when_no_mentions(self) -> None:
        """Text with no @ patterns returns an empty list."""
        result = extract_mentions("no mentions here")
        assert result == []

    def test_returns_empty_list_for_empty_string(self) -> None:
        """Empty string input returns an empty list."""
        result = extract_mentions("")
        assert result == []

    def test_ignores_bare_at_sign(self) -> None:
        """A bare @ not followed by word characters is not extracted."""
        result = extract_mentions("send to @ me")
        assert result == []

    def test_extracts_mention_at_start_of_string(self) -> None:
        """@username at the start of a string is extracted correctly."""
        result = extract_mentions("@carol thanks!")
        assert result == ["carol"]

    def test_extracts_mention_with_underscores(self) -> None:
        """@usernames containing underscores are extracted correctly."""
        result = extract_mentions("hey @john_doe")
        assert result == ["john_doe"]

    def test_three_distinct_mentions_in_order(self) -> None:
        """Three distinct mentions are returned in left-to-right order."""
        result = extract_mentions("@alice @bob @carol")
        assert result == ["alice", "bob", "carol"]
