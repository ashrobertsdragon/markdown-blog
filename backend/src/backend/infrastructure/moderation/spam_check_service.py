"""Spam detection service for comment text evaluation.

Provides configurable heuristic scoring for URL density, repeated characters,
and regex-based pattern matching.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field


@dataclass
class SpamCheckResult:
    """Result of a detailed spam check.

    Attributes:
        score: Spam score between 0 and 100 (inclusive).
        violations: Names of triggered checks, e.g. ``"url_density"``.
    """

    score: int
    violations: list[str] = field(default_factory=list)


class SpamCheckService:
    """Heuristic spam scoring service for comment text.

    Evaluates text against URL density, repeated characters, and an optional
    list of configurable regex patterns. Each triggered check contributes 25
    points to the score, capped at 100.
    """

    _URL_PATTERN: re.Pattern[str] = re.compile(r"https?://[^\s]+")
    _REPETITION_PATTERN: re.Pattern[str] = re.compile(r"(.)\1{4,}")

    def __init__(self, spam_patterns: list[str] | None = None) -> None:
        """Initialise the service with optional configurable spam patterns.

        Args:
            spam_patterns: List of regex strings to match against comment text.
                Each pattern is compiled once at construction time. Only the
                first matching pattern contributes to the score.
        """
        self._spam_patterns: list[re.Pattern[str]] = (
            [re.compile(p) for p in spam_patterns] if spam_patterns else []
        )

    def check(self, text: str) -> int:
        """Return a spam score for *text* between 0 and 100.

        Args:
            text: The comment body to evaluate.

        Returns:
            Integer spam score (0 = clean, 100 = definite spam).
        """
        return self.check_detailed(text).score

    def check_detailed(self, text: str) -> SpamCheckResult:
        """Return a detailed spam check result for *text*.

        Args:
            text: The comment body to evaluate.

        Returns:
            A :class:`SpamCheckResult` with the score and all violation names.
        """
        score = 0
        violations: list[str] = []

        url_count = len(self._URL_PATTERN.findall(text))
        if url_count > 2:
            score += 50
            violations.append("url_density")
        elif url_count == 2:
            score += 10

        if self._REPETITION_PATTERN.search(text):
            score += 25
            violations.append("repetition")

        for pattern in self._spam_patterns:
            if pattern.search(text):
                score += 25
                violations.append("known_pattern")
                break

        return SpamCheckResult(score=min(score, 100), violations=violations)
