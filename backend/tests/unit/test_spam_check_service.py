"""Unit tests for SpamCheckService and SpamCheckResult.

Tests describe the desired behavior of a spam scoring service that
evaluates comment text for URL density, repeated characters, and
configurable regex pattern matches.
"""

import time

from backend.infrastructure.moderation.spam_check_service import (
    SpamCheckResult,
    SpamCheckService,
)


class TestSpamCheckServiceNormalComments:
    """Tests for comments that should not be flagged as spam."""

    def test_allows_normal_comments(self) -> None:
        """Plain text returns a score below the spam threshold of 50."""
        service = SpamCheckService()
        score = service.check("Hello, great post!")
        assert score < 50

    def test_allows_urls_within_limit(self) -> None:
        """One or two URLs do not exceed the spam threshold of 50."""
        service = SpamCheckService()
        one_url = "Check this out: https://example.com"
        two_urls = "See https://example.com and https://other.com"
        assert service.check(one_url) < 50
        assert service.check(two_urls) < 50


class TestSpamCheckServiceUrlDensity:
    """Tests for URL density scoring."""

    def test_flags_excessive_urls(self) -> None:
        """Three or more URLs return a score at or above 50."""
        service = SpamCheckService()
        text = (
            "Visit https://one.com and https://two.com"
            " and https://three.com now!"
        )
        assert service.check(text) >= 50


class TestSpamCheckServiceRepeatedCharacters:
    """Tests for repeated character detection."""

    def test_detects_repeated_characters(self) -> None:
        """Five or more consecutive identical chars score at least 25."""
        service = SpamCheckService()
        assert service.check("aaaaaa") >= 25
        assert service.check("!!!!") < 25
        assert service.check("!!!!!") >= 25


class TestSpamCheckServiceConfigurablePatterns:
    """Tests for user-supplied regex spam patterns."""

    def test_matches_configurable_regex_patterns(self) -> None:
        """Text matching a caller-supplied pattern scores at least 25."""
        service = SpamCheckService(spam_patterns=["buy now"])
        assert service.check("Click here to buy now and save!") >= 25

    def test_non_matching_pattern_does_not_score(self) -> None:
        """Text not matching any pattern incurs no known_pattern violation."""
        service = SpamCheckService(spam_patterns=["buy now"])
        result = service.check_detailed("Hello, great post!")
        assert "known_pattern" not in result.violations


class TestSpamCheckServiceScoreCap:
    """Tests for score ceiling behaviour."""

    def test_mixed_spam_scoring_caps_at_100(self) -> None:
        """Combined violations never push the score above 100."""
        service = SpamCheckService(spam_patterns=["buy now"])
        text = (
            "buy now at https://a.com https://b.com https://c.com aaaaaabbbbb"
        )
        assert service.check(text) <= 100


class TestSpamCheckServiceReturnTypes:
    """Tests for return type contracts of check() and check_detailed()."""

    def test_check_returns_int(self) -> None:
        """check() returns an int, not a float."""
        service = SpamCheckService()
        result = service.check("Hello!")
        assert isinstance(result, int)

    def test_check_detailed_returns_spam_check_result(self) -> None:
        """check_detailed() returns a SpamCheckResult instance."""
        service = SpamCheckService()
        result = service.check_detailed("Hello!")
        assert isinstance(result, SpamCheckResult)
        assert hasattr(result, "score")
        assert hasattr(result, "violations")

    def test_spam_check_result_score_is_int(self) -> None:
        """SpamCheckResult.score is an int."""
        service = SpamCheckService()
        result = service.check_detailed("Hello!")
        assert isinstance(result.score, int)

    def test_spam_check_result_violations_is_list(self) -> None:
        """SpamCheckResult.violations is a list."""
        service = SpamCheckService()
        result = service.check_detailed("Hello!")
        assert isinstance(result.violations, list)


class TestSpamCheckServiceViolationReporting:
    """Tests for violation label accuracy in SpamCheckResult."""

    def test_check_detailed_reports_url_density_violation(self) -> None:
        """violations contains 'url_density' when more than two URLs present."""
        service = SpamCheckService()
        text = "https://one.com https://two.com https://three.com"
        result = service.check_detailed(text)
        assert "url_density" in result.violations

    def test_check_detailed_reports_repetition_violation(self) -> None:
        """violations contains 'repetition' for 5+ consecutive identical chars.

        Five or more of the same character in a row triggers the violation.
        """
        service = SpamCheckService()
        result = service.check_detailed("aaaaaa")
        assert "repetition" in result.violations

    def test_check_detailed_reports_known_pattern_violation(self) -> None:
        """violations contains 'known_pattern' when a pattern matches."""
        service = SpamCheckService(spam_patterns=["buy now"])
        result = service.check_detailed("Please buy now while stocks last")
        assert "known_pattern" in result.violations

    def test_clean_text_has_no_violations(self) -> None:
        """violations is empty for unambiguously clean text."""
        service = SpamCheckService()
        result = service.check_detailed("Hello, great post!")
        assert result.violations == []


class TestSpamCheckServicePerformance:
    """Tests for performance requirements."""

    def test_completes_under_100ms(self) -> None:
        """check() on a 5000-character string completes under 100ms."""
        service = SpamCheckService()
        text = "x" * 5000
        start = time.perf_counter()
        service.check(text)
        elapsed_ms = (time.perf_counter() - start) * 1000
        assert elapsed_ms < 100
