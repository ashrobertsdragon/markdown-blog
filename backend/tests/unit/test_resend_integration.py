"""Unit tests for Resend email integration.

Covers ResendSettings, ResendEmailService, ResendTemplateManager,
email_templates constants, and the get_resend_email_service dependency.

All HTTP calls are mocked via unittest.mock so no network access occurs.
"""

from unittest.mock import Mock, patch

import pytest
from pydantic import ValidationError

from backend.api.dependencies import get_resend_email_service
from backend.config import ResendSettings
from backend.infrastructure.email.email_templates import (
    POST_TITLE,
    REPLY_AUTHOR,
    TEMPLATE_DEFINITIONS,
    TEMPLATE_MENTION_NOTIFICATION,
    TEMPLATE_REPLY_NOTIFICATION,
)
from backend.infrastructure.email.resend_email_service import ResendEmailService
from backend.infrastructure.email.resend_template_manager import (
    ResendTemplateManager,
)

# ---------------------------------------------------------------------------
# ResendSettings
# ---------------------------------------------------------------------------


class TestResendSettings:
    """Tests for ResendSettings Pydantic model."""

    def test_resend_settings_loads_from_env(self, test_env) -> None:
        """ResendSettings should read RESEND_API_KEY from the environment.

        The test_env fixture sets RESEND_API_KEY=re_test_fake_key_for_testing,
        so the model must populate the field without raising.
        """
        settings = ResendSettings()
        assert settings.RESEND_API_KEY == "re_test_fake_key_for_testing"

    def test_resend_settings_requires_api_key(self, clean_env) -> None:
        """Missing RESEND_API_KEY must raise a ValidationError.

        The field has no default and is required. Instantiating without the
        variable in the environment must fail with a Pydantic ValidationError
        that mentions the missing field.
        """
        clean_env.delenv("RESEND_API_KEY", raising=False)
        with pytest.raises(ValidationError, match="RESEND_API_KEY"):
            ResendSettings()

    def test_resend_settings_has_default_template_aliases(
        self, test_env
    ) -> None:
        """ResendSettings must expose default aliases for both template types.

        The defaults must equal the canonical alias strings so email dispatch
        code can reference settings.TEMPLATE_REPLY_NOTIFICATION without
        needing a separate constant lookup.
        """
        settings = ResendSettings()
        assert settings.TEMPLATE_REPLY_NOTIFICATION == "reply-notification"
        assert settings.TEMPLATE_MENTION_NOTIFICATION == "mention-notification"

    def test_resend_settings_domain_configurable(self, test_env) -> None:
        """RESEND_DOMAIN must be read from the environment when set.

        Callers configure the sending domain per-environment. The value must
        survive the round-trip through Pydantic validation unchanged.
        """
        test_env.setenv("RESEND_DOMAIN", "blog.example.com")
        settings = ResendSettings()
        assert settings.RESEND_DOMAIN == "blog.example.com"

    def test_resend_max_retries_must_be_at_least_1(self, test_env) -> None:
        """RESEND_MAX_RETRIES=0 must raise a ValidationError.

        Zero retries means the first failure is permanent with no recovery
        attempt. The field must enforce a minimum of 1 to ensure the retry
        loop is meaningful and misconfiguration is caught at startup.
        """
        test_env.setenv("RESEND_MAX_RETRIES", "0")
        with pytest.raises(ValidationError):
            ResendSettings()

    def test_resend_request_timeout_must_be_at_least_1(self, test_env) -> None:
        """RESEND_REQUEST_TIMEOUT=0 must raise a ValidationError.

        A zero-second timeout causes every request to fail immediately before
        any network activity. The field must enforce a minimum of 1 second to
        prevent silent misconfiguration that would break all email delivery.
        """
        test_env.setenv("RESEND_REQUEST_TIMEOUT", "0")
        with pytest.raises(ValidationError):
            ResendSettings()


# ---------------------------------------------------------------------------
# ResendEmailService
# ---------------------------------------------------------------------------


@pytest.fixture
def resend_service(test_env) -> ResendEmailService:
    """ResendEmailService configured with a test API key."""
    return ResendEmailService(api_key="re_test_fake_key_for_testing")


class TestResendEmailService:
    """Tests for ResendEmailService send behaviour."""

    def test_send_email_success(self, resend_service) -> None:
        """A 200 response from the Resend API must return the email_id string.

        The service wraps the HTTP call and extracts the id field from the
        JSON body. Callers use this id to correlate delivery receipts.
        """
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"id": "email_abc123"}

        with patch("requests.post", return_value=mock_response):
            result = resend_service.send_email(
                to="user@example.com",
                subject="Test Subject",
                html="<p>Hello</p>",
            )

        assert result == "email_abc123"

    def test_send_email_rate_limited_retries(self, resend_service) -> None:
        """A 429 response must trigger exponential backoff and retry up to 3x.

        The service must not give up on the first rate-limit response. After
        retrying, it must return the email_id from the eventual 200 response.
        Sleep calls verify that backoff actually occurred between attempts.
        """
        rate_limited = Mock()
        rate_limited.status_code = 429

        success = Mock()
        success.status_code = 200
        success.json.return_value = {"id": "email_after_retry"}

        with patch(
            "requests.post", side_effect=[rate_limited, rate_limited, success]
        ):
            with patch("time.sleep") as mock_sleep:
                result = resend_service.send_email(
                    to="user@example.com",
                    subject="Test",
                    html="<p>hi</p>",
                )

        assert result == "email_after_retry"
        assert mock_sleep.call_count >= 2

    def test_send_email_server_error_retries(self, resend_service) -> None:
        """A 5xx response must be retried and return the email_id on success.

        Transient server errors must not be treated as permanent failures.
        The service must retry and surface the eventual success to callers.
        """
        server_error = Mock()
        server_error.status_code = 503

        success = Mock()
        success.status_code = 200
        success.json.return_value = {"id": "email_recovered"}

        with patch("requests.post", side_effect=[server_error, success]):
            with patch("time.sleep"):
                result = resend_service.send_email(
                    to="user@example.com",
                    subject="Test",
                    html="<p>hi</p>",
                )

        assert result == "email_recovered"

    def test_send_email_client_error_permanent_failure(
        self, resend_service
    ) -> None:
        """A 4xx response (not 429) must return None immediately without retry.

        Client errors such as 400 Bad Request or 422 Unprocessable Entity
        signal invalid input that retrying cannot fix. Returning None signals
        permanent failure to the caller without raising an exception.
        """
        bad_request = Mock()
        bad_request.status_code = 400
        bad_request.json.return_value = {"message": "Invalid email address"}

        with patch("requests.post", return_value=bad_request) as mock_post:
            result = resend_service.send_email(
                to="not-an-email",
                subject="Test",
                html="<p>hi</p>",
            )

        assert result is None
        assert mock_post.call_count == 1

    def test_send_email_timeout_returns_none(self, resend_service) -> None:
        """A network timeout must return None without propagating the exception.

        The service must treat transport-level errors as soft failures. The
        caller is responsible for scheduling a retry via the notification queue.
        """
        import requests as req

        with patch("requests.post", side_effect=req.Timeout("timed out")):
            result = resend_service.send_email(
                to="user@example.com",
                subject="Test",
                html="<p>hi</p>",
            )

        assert result is None

    def test_send_email_returns_none_on_max_retries_exceeded(
        self, resend_service
    ) -> None:
        """Exhausting all 3 retry attempts must return None.

        After MAX_RETRIES failed attempts the service must give up and return
        None rather than raising. This keeps the caller's control flow simple
        and delegates retry scheduling to the notification queue.
        """
        rate_limited = Mock()
        rate_limited.status_code = 429

        with patch("requests.post", return_value=rate_limited):
            with patch("time.sleep"):
                result = resend_service.send_email(
                    to="user@example.com",
                    subject="Test",
                    html="<p>hi</p>",
                )

        assert result is None

    def test_send_email_makes_correct_number_of_attempts_on_rate_limit(
        self, resend_service
    ) -> None:
        """All 429 responses must exhaust exactly max_retries + 1 attempts.

        The retry loop runs for attempt in range(max_retries + 1), so with
        the default max_retries=3 the service must make exactly 4 POST
        requests before giving up. Verifying call_count guards against
        off-by-one bugs where retries stop too early or continue past the
        configured limit.
        """
        rate_limited = Mock()
        rate_limited.status_code = 429

        with patch("requests.post", return_value=rate_limited) as mock_post:
            with patch("time.sleep"):
                resend_service.send_email(
                    to="user@example.com",
                    subject="Test",
                    html="<p>hi</p>",
                )

        expected_total_attempts = resend_service._max_retries + 1
        assert mock_post.call_count == expected_total_attempts

    def test_send_email_response_missing_id_field_returns_none(
        self, resend_service
    ) -> None:
        """A 200 response body without an 'id' key must return None.

        The service extracts response.json()['id'] and catches KeyError,
        returning None instead of propagating. Callers must not receive a
        partial or undefined email identifier when Resend omits the field.
        """
        missing_id_response = Mock()
        missing_id_response.status_code = 200
        missing_id_response.json.return_value = {}

        with patch("requests.post", return_value=missing_id_response):
            result = resend_service.send_email(
                to="user@example.com",
                subject="Test",
                html="<p>hi</p>",
            )

        assert result is None


# ---------------------------------------------------------------------------
# ResendTemplateManager
# ---------------------------------------------------------------------------


@pytest.fixture
def template_manager(test_env) -> ResendTemplateManager:
    """ResendTemplateManager configured with a test API key."""
    return ResendTemplateManager(api_key="re_test_fake_key_for_testing")


class TestResendTemplateManager:
    """Tests for ResendTemplateManager CRUD operations."""

    def test_create_template_success(self, template_manager) -> None:
        """A 200 response must return the new template_id string.

        The manager extracts id from the response body and returns it so
        callers can store the identifier for subsequent publish and reference.
        """
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"id": "tmpl_xyz789"}

        with patch("requests.post", return_value=mock_response):
            result = template_manager.create_template(
                name="Reply Notification",
                alias="reply-notification",
                subject="Someone replied",
                html="<p>{{{REPLY_AUTHOR}}} replied</p>",
            )

        assert result == "tmpl_xyz789"

    def test_create_template_already_exists_raises(
        self, template_manager
    ) -> None:
        """A 409 Conflict must raise an error.

        The manager enforces a create-only policy: templates may not be
        silently overwritten. A 409 signals that the alias is already taken
        and the caller must decide how to reconcile.
        """
        conflict = Mock()
        conflict.status_code = 409
        conflict.json.return_value = {
            "message": "Template alias already exists"
        }

        with patch("requests.post", return_value=conflict):
            with pytest.raises(Exception, match="already exists"):
                template_manager.create_template(
                    name="Reply Notification",
                    alias="reply-notification",
                    subject="Someone replied",
                    html="<p>hi</p>",
                )

    def test_create_template_server_error_returns_none(
        self, template_manager
    ) -> None:
        """A 5xx response during template creation must return None.

        Transient server errors during provisioning must not raise so that
        idempotent setup scripts can log the failure and continue.
        """
        server_error = Mock()
        server_error.status_code = 500

        with patch("requests.post", return_value=server_error):
            result = template_manager.create_template(
                name="Mention Notification",
                alias="mention-notification",
                subject="You were mentioned",
                html="<p>hi</p>",
            )

        assert result is None

    def test_publish_template_success(self, template_manager) -> None:
        """Publishing an existing template must return True on 200.

        A published template becomes active in Resend's delivery pipeline.
        Returning True gives callers a clear success signal without needing
        to inspect response bodies.
        """
        mock_response = Mock()
        mock_response.status_code = 200

        with patch("requests.post", return_value=mock_response):
            result = template_manager.publish_template("tmpl_xyz789")

        assert result is True

    def test_publish_template_not_found_returns_false(
        self, template_manager
    ) -> None:
        """A 404 during publish must return False.

        The template may have been deleted between creation and publish.
        Returning False allows callers to detect the gap and recreate if needed.
        """
        not_found = Mock()
        not_found.status_code = 404

        with patch("requests.post", return_value=not_found):
            result = template_manager.publish_template("tmpl_missing")

        assert result is False

    def test_get_template_success(self, template_manager) -> None:
        """A 200 response must return a dict containing id and alias.

        Callers inspect the returned dict to verify template state before
        dispatching emails. At minimum id and alias must be present.
        """
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "id": "tmpl_xyz789",
            "alias": "reply-notification",
            "name": "Reply Notification",
        }

        with patch("requests.get", return_value=mock_response):
            result = template_manager.get_template("tmpl_xyz789")

        assert result is not None
        assert result["id"] == "tmpl_xyz789"
        assert result["alias"] == "reply-notification"

    def test_delete_template_success(self, template_manager) -> None:
        """A 200 response from the delete endpoint must return True.

        Returning a bool keeps the caller's control flow simple and avoids
        propagating HTTP semantics outside the infrastructure layer.
        """
        mock_response = Mock()
        mock_response.status_code = 200

        with patch("requests.delete", return_value=mock_response):
            result = template_manager.delete_template("tmpl_xyz789")

        assert result is True

    def test_create_template_network_timeout_returns_none(
        self, template_manager
    ) -> None:
        """A network timeout during template creation must return None.

        Transport-level failures must not propagate out of the infrastructure
        layer. Provisioning scripts rely on None to detect and log the failure
        without an unhandled exception aborting the entire setup run.
        """
        import requests as req

        with patch("requests.post", side_effect=req.Timeout("timed out")):
            result = template_manager.create_template(
                name="Reply Notification",
                alias="reply-notification",
                subject="Someone replied",
                html="<p>{{{REPLY_AUTHOR}}} replied</p>",
            )

        assert result is None

    def test_create_template_connection_error_returns_none(
        self, template_manager
    ) -> None:
        """A connection error during template creation must return None.

        RequestException covers DNS failures, refused connections, and other
        transport errors. None signals soft failure so the caller can retry
        without catching implementation-specific exception types.
        """
        import requests as req

        with patch(
            "requests.post",
            side_effect=req.RequestException("connection refused"),
        ):
            result = template_manager.create_template(
                name="Reply Notification",
                alias="reply-notification",
                subject="Someone replied",
                html="<p>{{{REPLY_AUTHOR}}} replied</p>",
            )

        assert result is None

    def test_publish_template_network_timeout_returns_false(
        self, template_manager
    ) -> None:
        """A network timeout during publish must return False.

        publish_template returns a bool contract. A transport failure must
        map to False rather than propagating so callers handle it uniformly
        alongside 404 and other non-success outcomes.
        """
        import requests as req

        with patch("requests.post", side_effect=req.Timeout("timed out")):
            result = template_manager.publish_template("tmpl_xyz789")

        assert result is False

    def test_get_template_network_timeout_returns_none(
        self, template_manager
    ) -> None:
        """A network timeout during get_template must return None.

        The caller treats None as "template not available" regardless of
        whether it was absent or unreachable. Propagating Timeout would
        require callers to handle both None and exceptions for the same case.
        """
        import requests as req

        with patch("requests.get", side_effect=req.Timeout("timed out")):
            result = template_manager.get_template("tmpl_xyz789")

        assert result is None

    def test_delete_template_network_timeout_returns_false(
        self, template_manager
    ) -> None:
        """A network timeout during delete_template must return False.

        Returning False on transport failure is consistent with the bool
        contract of delete_template and avoids leaking HTTP-layer exceptions
        into provisioning or cleanup scripts.
        """
        import requests as req

        with patch("requests.delete", side_effect=req.Timeout("timed out")):
            result = template_manager.delete_template("tmpl_xyz789")

        assert result is False

    def test_create_template_response_missing_id_returns_none(
        self, template_manager
    ) -> None:
        """A 201 response body without an 'id' key must return None.

        The manager extracts response.json()['id'] on success. If Resend
        returns a 2xx without that field the manager must not raise a
        KeyError — it must return None so callers can detect the anomaly.
        """
        missing_id_response = Mock()
        missing_id_response.status_code = 201
        missing_id_response.json.return_value = {}

        with patch("requests.post", return_value=missing_id_response):
            result = template_manager.create_template(
                name="Reply Notification",
                alias="reply-notification",
                subject="Someone replied",
                html="<p>{{{REPLY_AUTHOR}}} replied</p>",
            )

        assert result is None


# ---------------------------------------------------------------------------
# email_templates constants
# ---------------------------------------------------------------------------


class TestEmailTemplateConstants:
    """Tests for email_templates module constants and definitions."""

    def test_reply_notification_alias_constant(self) -> None:
        """TEMPLATE_REPLY_NOTIFICATION must equal 'reply-notification'.

        The alias string is the stable identifier used when dispatching emails
        via the Resend templates API. It must not change between deployments.
        """
        assert TEMPLATE_REPLY_NOTIFICATION == "reply-notification"

    def test_mention_notification_alias_constant(self) -> None:
        """TEMPLATE_MENTION_NOTIFICATION must equal 'mention-notification'.

        Same stability requirement as TEMPLATE_REPLY_NOTIFICATION — the alias
        is a contract between this service and the Resend template registry.
        """
        assert TEMPLATE_MENTION_NOTIFICATION == "mention-notification"

    def test_template_variables_defined(self) -> None:
        """REPLY_AUTHOR and POST_TITLE variable name constants must exist.

        These constants prevent magic-string bugs when building template
        variable payloads. At minimum REPLY_AUTHOR and POST_TITLE are required
        by both notification template HTML bodies.
        """
        assert REPLY_AUTHOR is not None
        assert POST_TITLE is not None
        assert isinstance(REPLY_AUTHOR, str)
        assert isinstance(POST_TITLE, str)

    def test_template_definitions_have_required_fields(self) -> None:
        """Every entry in TEMPLATE_DEFINITIONS must contain name, subject, html.

        The provisioning script iterates TEMPLATE_DEFINITIONS to register
        templates with Resend. Missing fields would cause silent failures
        or malformed API requests at deploy time.
        """
        assert len(TEMPLATE_DEFINITIONS) > 0
        for alias, definition in TEMPLATE_DEFINITIONS.items():
            assert "name" in definition, f"Template '{alias}' missing 'name'"
            assert "subject" in definition, (
                f"Template '{alias}' missing 'subject'"
            )
            assert "html" in definition, f"Template '{alias}' missing 'html'"

    def test_template_html_uses_triple_mustache(self) -> None:
        """Template HTML bodies must use triple-mustache syntax for variables.

        Resend's template engine uses {{{variable}}} for unescaped HTML
        interpolation. Double-mustache would escape angle brackets in reply
        content and produce corrupted email bodies.
        """
        for alias, definition in TEMPLATE_DEFINITIONS.items():
            assert "{{{" in definition["html"], (
                f"Template '{alias}' HTML does not use triple-mustache syntax"
            )


# ---------------------------------------------------------------------------
# Dependency injection
# ---------------------------------------------------------------------------


class TestGetResendEmailService:
    """Tests for the get_resend_email_service dependency function."""

    def test_get_resend_email_service_returns_instance(self, test_env) -> None:
        """get_resend_email_service() must return a ResendEmailService instance.

        The dependency function is the sole construction path for callers
        outside the infrastructure layer. The returned object must be the
        concrete service type so callers can rely on its full interface.
        """
        import backend.api.dependencies as deps

        deps._resend_email_service = None
        try:
            service = get_resend_email_service()
            assert isinstance(service, ResendEmailService)
        finally:
            deps._resend_email_service = None

    def test_get_resend_email_service_is_singleton(self, test_env) -> None:
        """Two calls to get_resend_email_service() must return the same object.

        The service holds no per-request state and is safe to share. A
        singleton avoids unnecessary object allocation on every HTTP request
        and keeps connection-pool semantics consistent.
        """
        import backend.api.dependencies as deps

        deps._resend_email_service = None
        try:
            first = get_resend_email_service()
            second = get_resend_email_service()
            assert first is second
        finally:
            deps._resend_email_service = None
