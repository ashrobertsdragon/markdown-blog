"""Domain service for @mention extraction from comment text."""

import re


def extract_mentions(text: str) -> list[str]:
    """Extract unique @mention usernames from text.

    Parses the text for patterns matching @word_characters and returns a
    deduplicated list preserving first-seen order.

    Args:
        text: The comment text to search for @mentions.

    Returns:
        List of unique usernames (without the @ prefix), in first-seen order.

    Example:
        >>> extract_mentions("Hello @alice and @bob")
        ['alice', 'bob']
        >>> extract_mentions("@alice @alice")
        ['alice']
    """
    seen: set[str] = set()
    result: list[str] = []
    for username in re.findall(r"@(\w+)", text):
        if username not in seen:
            seen.add(username)
            result.append(username)
    return result
