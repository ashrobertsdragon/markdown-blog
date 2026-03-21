"""Integration tests asserting the notifications documentation file exists and is complete."""

from pathlib import Path

DOCS_PATH = (
    Path(__file__).parent.parent.parent.parent / "docs" / "notifications.md"
)


def _read_docs() -> str:
    """Read the notifications documentation file."""
    return DOCS_PATH.read_text(encoding="utf-8")


class TestNotificationsDocFileExists:
    """Assert the documentation file is present."""

    def test_docs_file_exists(self) -> None:
        """monorepo/docs/notifications.md must exist."""
        assert DOCS_PATH.exists(), (
            f"Documentation file not found at {DOCS_PATH}. "
            "Create monorepo/docs/notifications.md."
        )


class TestNotificationsDocEndpointCoverage:
    """Assert each notification endpoint is referenced in the documentation."""

    def test_preferences_endpoint_documented(self) -> None:
        """Documentation must reference /user/notification-preferences."""
        content = _read_docs()
        assert "/user/notification-preferences" in content, (
            "notifications.md must document the /user/notification-preferences endpoint"
        )

    def test_admin_notifications_endpoint_documented(self) -> None:
        """Documentation must reference /admin/notifications."""
        content = _read_docs()
        assert "/admin/notifications" in content, (
            "notifications.md must document the /admin/notifications endpoint"
        )

    def test_unsubscribe_endpoint_documented(self) -> None:
        """Documentation must reference /unsubscribe."""
        content = _read_docs()
        assert "/unsubscribe" in content, (
            "notifications.md must document the /unsubscribe endpoint"
        )


class TestNotificationsDocEnvironmentVariables:
    """Assert critical environment variables are mentioned in the documentation."""

    def test_resend_api_key_mentioned(self) -> None:
        """Documentation must mention RESEND_API_KEY."""
        content = _read_docs()
        assert "RESEND_API_KEY" in content, (
            "notifications.md must mention the RESEND_API_KEY environment variable"
        )

    def test_unsubscribe_secret_mentioned(self) -> None:
        """Documentation must mention UNSUBSCRIBE_SECRET."""
        content = _read_docs()
        assert "UNSUBSCRIBE_SECRET" in content, (
            "notifications.md must mention the UNSUBSCRIBE_SECRET environment variable"
        )


class TestNotificationsDocReliabilityPatterns:
    """Assert retry/backoff behaviour is documented."""

    def test_retry_or_backoff_mentioned(self) -> None:
        """Documentation must mention retry or backoff behaviour."""
        content = _read_docs()
        mentions_retry_or_backoff = (
            "retry" in content.lower() or "backoff" in content.lower()
        )
        assert mentions_retry_or_backoff, (
            "notifications.md must document retry or backoff behaviour"
        )
