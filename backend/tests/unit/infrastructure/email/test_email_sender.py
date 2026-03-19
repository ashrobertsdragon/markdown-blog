"""Unit tests for EmailSender.

Covers:
- Template alias resolution: EventType → Resend template alias
- Successful send returns Resend email ID
- 429 rate-limit triggers exponential backoff and retries
- 5xx server errors trigger exponential backoff and retries
- 4xx client errors return None immediately (permanent failure, no retry)
- Network timeout returns None immediately
- RequestException returns None immediately
- Missing 'id' in success response returns None
- Exhausted retries return None
- Unmapped EventType raises ValueError
- POST payload contains template_id and variables (not html)
"""

from unittest.mock import Mock, patch

import pytest
import requests as req

from backend.domain.aggregates.notification import EventType
from backend.infrastructure.email.email_sender import EmailSender

_PATCH_POST = "backend.infrastructure.email.email_sender.requests.post"
_PATCH_SLEEP = "backend.infrastructure.email.email_sender.time.sleep"

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def sender() -> EmailSender:
    """EmailSender with test API key and default template mapping."""
    return EmailSender(
        api_key="re_test_key",
        domain="noreply@test.example.com",
        timeout=5,
        max_retries=3,
    )


@pytest.fixture
def success_response() -> Mock:
    """Mock Resend 200 success response with email id."""
    resp = Mock()
    resp.status_code = 200
    resp.json.return_value = {"id": "email_abc123"}
    return resp


@pytest.fixture
def rate_limit_response() -> Mock:
    """Mock Resend 429 rate-limit response."""
    resp = Mock()
    resp.status_code = 429
    return resp


@pytest.fixture
def server_error_response() -> Mock:
    """Mock Resend 503 server error response."""
    resp = Mock()
    resp.status_code = 503
    return resp


@pytest.fixture
def bad_request_response() -> Mock:
    """Mock Resend 400 bad request response."""
    resp = Mock()
    resp.status_code = 400
    resp.json.return_value = {"message": "Invalid template variables"}
    return resp


@pytest.fixture
def reply_variables() -> dict[str, str]:
    """Minimal variables for the reply-notification template."""
    return {
        "REPLY_AUTHOR": "Jane",
        "POST_TITLE": "My Post",
        "ORIGINAL_COMMENT": "Great post!",
        "REPLY_EXCERPT": "Thanks!",
        "POST_URL": "https://example.com/post",
        "UNSUBSCRIBE_URL": "https://example.com/unsubscribe?token=abc",
    }


# ---------------------------------------------------------------------------
# Template resolution
# ---------------------------------------------------------------------------


class TestTemplateResolution:
    """Tests for EventType → template alias mapping."""

    def test_reply_received_maps_to_reply_notification_alias(
        self, sender: EmailSender
    ) -> None:
        """REPLY_RECEIVED must resolve to the reply-notification alias.

        This alias is the stable Resend template identifier for reply emails.
        A change here would break delivery for all reply notifications.
        """
        alias = sender._resolve_template_alias(EventType.REPLY_RECEIVED)
        assert alias == "reply-notification"

    def test_comment_posted_maps_to_reply_notification_alias(
        self, sender: EmailSender
    ) -> None:
        """COMMENT_POSTED must resolve to a valid template alias.

        Post authors receive a notification when someone comments. The alias
        must map to an existing Resend template so the send does not fail
        immediately with a template-not-found error.
        """
        alias = sender._resolve_template_alias(EventType.COMMENT_POSTED)
        assert alias == "reply-notification"

    def test_custom_template_map_overrides_defaults(self) -> None:
        """A caller-supplied template_map must override built-in defaults.

        Operators must be able to swap aliases without code changes, for
        example to use a different template per environment.
        """
        custom = {EventType.REPLY_RECEIVED: "custom-reply-template"}
        sender = EmailSender(
            api_key="re_test",
            domain="noreply@example.com",
            template_map=custom,
        )
        assert (
            sender._resolve_template_alias(EventType.REPLY_RECEIVED)
            == "custom-reply-template"
        )


# ---------------------------------------------------------------------------
# Successful send
# ---------------------------------------------------------------------------


class TestSuccessfulSend:
    """Tests for the happy-path send flow."""

    def test_send_returns_email_id_on_200(
        self,
        sender: EmailSender,
        success_response: Mock,
        reply_variables: dict[str, str],
    ) -> None:
        """A 200 response must return the Resend email ID string.

        The email ID is stored on the Notification record for delivery
        tracking and admin debugging via the Resend dashboard.
        """
        with patch(
            _PATCH_POST,
            return_value=success_response,
        ):
            result = sender.send(
                to="user@example.com",
                event_type=EventType.REPLY_RECEIVED,
                variables=reply_variables,
            )

        assert result == "email_abc123"

    def test_send_returns_email_id_on_201(
        self,
        sender: EmailSender,
        reply_variables: dict[str, str],
    ) -> None:
        """A 201 Created response must also return the email ID.

        Resend may return 200 or 201 depending on API version. Both are
        valid success responses and must be handled identically.
        """
        created = Mock()
        created.status_code = 201
        created.json.return_value = {"id": "email_201_id"}

        with patch(
            _PATCH_POST,
            return_value=created,
        ):
            result = sender.send(
                to="user@example.com",
                event_type=EventType.REPLY_RECEIVED,
                variables=reply_variables,
            )

        assert result == "email_201_id"

    def test_send_posts_to_resend_emails_endpoint(
        self,
        sender: EmailSender,
        success_response: Mock,
        reply_variables: dict[str, str],
    ) -> None:
        """send() must POST to the Resend /emails endpoint.

        The emails endpoint is the sole delivery path; posting to the wrong
        URL would silently fail with a 404 that looks like a client error.
        """
        with patch(
            _PATCH_POST,
            return_value=success_response,
        ) as mock_post:
            sender.send(
                to="user@example.com",
                event_type=EventType.REPLY_RECEIVED,
                variables=reply_variables,
            )

        url = mock_post.call_args[0][0]
        assert "api.resend.com/emails" in url

    def test_send_payload_contains_template_id_not_html(
        self,
        sender: EmailSender,
        success_response: Mock,
        reply_variables: dict[str, str],
    ) -> None:
        """POST payload must include template_id and must NOT include html.

        EmailSender uses Resend's template-based send path. Sending raw html
        would bypass the managed template, breaking formatting consistency
        and bypassing Resend's plain-text fallback generation.
        """
        with patch(
            _PATCH_POST,
            return_value=success_response,
        ) as mock_post:
            sender.send(
                to="user@example.com",
                event_type=EventType.REPLY_RECEIVED,
                variables=reply_variables,
            )

        payload = mock_post.call_args[1]["json"]
        assert "html" not in payload
        assert "subject" not in payload
        assert "template_id" in payload or "template" in payload

    def test_send_payload_contains_variables(
        self,
        sender: EmailSender,
        success_response: Mock,
        reply_variables: dict[str, str],
    ) -> None:
        """POST payload must include the variables dict for template rendering.

        Without variables the template renders with empty placeholders, which
        produces emails with blank author names, post titles, and URLs.
        """
        with patch(
            _PATCH_POST,
            return_value=success_response,
        ) as mock_post:
            sender.send(
                to="user@example.com",
                event_type=EventType.REPLY_RECEIVED,
                variables=reply_variables,
            )

        payload = mock_post.call_args[1]["json"]
        assert "variables" in payload
        assert payload["variables"]["REPLY_AUTHOR"] == "Jane"

    def test_send_payload_contains_from_and_to(
        self,
        sender: EmailSender,
        success_response: Mock,
        reply_variables: dict[str, str],
    ) -> None:
        """POST payload must include from and to email addresses.

        Missing from causes Resend to reject the request with 422. Missing to
        means the email is addressed to nobody and silently discarded.
        """
        with patch(
            _PATCH_POST,
            return_value=success_response,
        ) as mock_post:
            sender.send(
                to="recipient@example.com",
                event_type=EventType.REPLY_RECEIVED,
                variables=reply_variables,
            )

        payload = mock_post.call_args[1]["json"]
        assert payload["to"] == "recipient@example.com"
        assert payload["from"] == "noreply@test.example.com"

    def test_send_uses_bearer_auth_header(
        self,
        sender: EmailSender,
        success_response: Mock,
        reply_variables: dict[str, str],
    ) -> None:
        """POST request must include Authorization: Bearer header.

        Resend requires bearer token authentication on all requests. A missing
        or malformed header returns 401 and the notification is not delivered.
        """
        with patch(
            _PATCH_POST,
            return_value=success_response,
        ) as mock_post:
            sender.send(
                to="user@example.com",
                event_type=EventType.REPLY_RECEIVED,
                variables=reply_variables,
            )

        headers = mock_post.call_args[1]["headers"]
        assert headers["Authorization"] == "Bearer re_test_key"


# ---------------------------------------------------------------------------
# Rate limit handling (429)
# ---------------------------------------------------------------------------


class TestRateLimitHandling:
    """Tests for 429 rate-limit retry behaviour."""

    def test_429_triggers_retry_and_returns_id_on_success(
        self,
        sender: EmailSender,
        rate_limit_response: Mock,
        success_response: Mock,
        reply_variables: dict[str, str],
    ) -> None:
        """A 429 must not be treated as permanent; retry must succeed.

        Resend rate-limits at the API key level. A single 429 is transient
        and the next attempt at a lower request rate must succeed normally.
        """
        with patch(
            "requests.post", side_effect=[rate_limit_response, success_response]
        ):
            with patch(_PATCH_SLEEP):
                result = sender.send(
                    to="user@example.com",
                    event_type=EventType.REPLY_RECEIVED,
                    variables=reply_variables,
                )

        assert result == "email_abc123"

    def test_429_triggers_exponential_backoff_sleep(
        self,
        sender: EmailSender,
        rate_limit_response: Mock,
        success_response: Mock,
        reply_variables: dict[str, str],
    ) -> None:
        """Each 429 must call time.sleep with an exponentially increasing delay.

        Sleeping before retry reduces load on Resend's API and avoids
        immediately re-hitting the rate limit on the next attempt.
        """
        with patch(
            "requests.post",
            side_effect=[
                rate_limit_response,
                rate_limit_response,
                success_response,
            ],
        ):
            with patch(_PATCH_SLEEP) as mock_sleep:
                sender.send(
                    to="user@example.com",
                    event_type=EventType.REPLY_RECEIVED,
                    variables=reply_variables,
                )

        assert mock_sleep.call_count >= 2
        delays = [c.args[0] for c in mock_sleep.call_args_list]
        assert delays[1] > delays[0]

    def test_429_exhausted_retries_returns_none(
        self,
        sender: EmailSender,
        rate_limit_response: Mock,
        reply_variables: dict[str, str],
    ) -> None:
        """Exhausting all retries on 429 must return None.

        The notification queue will schedule a future retry. Returning None
        signals failure without raising so the caller's control flow stays
        simple.
        """
        with patch(
            _PATCH_POST,
            return_value=rate_limit_response,
        ):
            with patch(_PATCH_SLEEP):
                result = sender.send(
                    to="user@example.com",
                    event_type=EventType.REPLY_RECEIVED,
                    variables=reply_variables,
                )

        assert result is None

    def test_429_makes_exactly_max_retries_plus_one_attempts(
        self,
        sender: EmailSender,
        rate_limit_response: Mock,
        reply_variables: dict[str, str],
    ) -> None:
        """With max_retries=3 and all 429s, exactly 4 POST calls must be made.

        The retry loop runs for attempt in range(max_retries + 1). An off-by-one
        would either give up too early or loop forever.
        """
        with patch(
            "requests.post", return_value=rate_limit_response
        ) as mock_post:
            with patch(_PATCH_SLEEP):
                sender.send(
                    to="user@example.com",
                    event_type=EventType.REPLY_RECEIVED,
                    variables=reply_variables,
                )

        assert mock_post.call_count == sender._max_retries + 1


# ---------------------------------------------------------------------------
# Server error handling (5xx)
# ---------------------------------------------------------------------------


class TestServerErrorHandling:
    """Tests for 5xx retry behaviour."""

    def test_5xx_triggers_retry_and_succeeds(
        self,
        sender: EmailSender,
        server_error_response: Mock,
        success_response: Mock,
        reply_variables: dict[str, str],
    ) -> None:
        """A 5xx must be retried and return the email ID on eventual success.

        Transient Resend infrastructure failures must not cause permanent
        notification loss. The retry must succeed if the service recovers.
        """
        with patch(
            "requests.post",
            side_effect=[server_error_response, success_response],
        ):
            with patch(_PATCH_SLEEP):
                result = sender.send(
                    to="user@example.com",
                    event_type=EventType.REPLY_RECEIVED,
                    variables=reply_variables,
                )

        assert result == "email_abc123"

    def test_5xx_exhausted_retries_returns_none(
        self,
        sender: EmailSender,
        server_error_response: Mock,
        reply_variables: dict[str, str],
    ) -> None:
        """Exhausting all retries on 5xx must return None.

        Prolonged outages eventually exceed the retry budget. None signals
        the caller to schedule re-delivery via the notification queue.
        """
        with patch(
            _PATCH_POST,
            return_value=server_error_response,
        ):
            with patch(_PATCH_SLEEP):
                result = sender.send(
                    to="user@example.com",
                    event_type=EventType.REPLY_RECEIVED,
                    variables=reply_variables,
                )

        assert result is None

    def test_500_and_503_both_trigger_retry(
        self,
        sender: EmailSender,
        success_response: Mock,
        reply_variables: dict[str, str],
    ) -> None:
        """Both 500 and 503 must trigger the retry path.

        Multiple 5xx codes indicate server-side problems. Treating only one
        code as retryable would let the other become a silent permanent failure.
        """
        for status_code in (500, 502, 503, 504):
            error = Mock()
            error.status_code = status_code

            with patch(
                _PATCH_POST,
                side_effect=[error, success_response],
            ):
                with patch(_PATCH_SLEEP):
                    result = sender.send(
                        to="user@example.com",
                        event_type=EventType.REPLY_RECEIVED,
                        variables=reply_variables,
                    )

            assert result == "email_abc123", (
                f"Expected retry success for HTTP {status_code}"
            )


# ---------------------------------------------------------------------------
# Permanent failure (4xx)
# ---------------------------------------------------------------------------


class TestPermanentFailure:
    """Tests for 4xx permanent failure behaviour."""

    def test_400_returns_none_immediately(
        self,
        sender: EmailSender,
        bad_request_response: Mock,
        reply_variables: dict[str, str],
    ) -> None:
        """A 400 Bad Request must return None with no retry attempt.

        Invalid payloads cannot succeed by retrying. A single attempt is
        sufficient to confirm permanent failure.
        """
        with patch(
            "requests.post", return_value=bad_request_response
        ) as mock_post:
            result = sender.send(
                to="user@example.com",
                event_type=EventType.REPLY_RECEIVED,
                variables=reply_variables,
            )

        assert result is None
        assert mock_post.call_count == 1

    @pytest.mark.parametrize("status_code", [401, 403, 404, 422])
    def test_4xx_non_429_returns_none_with_single_attempt(
        self,
        sender: EmailSender,
        reply_variables: dict[str, str],
        status_code: int,
    ) -> None:
        """Any 4xx except 429 must return None after a single attempt.

        These codes signal client-side errors: unauthorized, forbidden,
        not found, or validation failure. Retrying will not fix them.
        """
        error_response = Mock()
        error_response.status_code = status_code

        with patch(
            _PATCH_POST,
            return_value=error_response,
        ) as mock_post:
            result = sender.send(
                to="user@example.com",
                event_type=EventType.REPLY_RECEIVED,
                variables=reply_variables,
            )

        assert result is None
        assert mock_post.call_count == 1


# ---------------------------------------------------------------------------
# Network errors
# ---------------------------------------------------------------------------


class TestNetworkErrors:
    """Tests for transport-level failure handling."""

    def test_timeout_returns_none_immediately(
        self,
        sender: EmailSender,
        reply_variables: dict[str, str],
    ) -> None:
        """A network timeout must return None without propagating.

        Timeouts are treated as transient; the notification queue will
        schedule a retry. Propagating Timeout would require callers to
        catch both exceptions and None, complicating their control flow.
        """
        with patch(
            _PATCH_POST,
            side_effect=req.Timeout("timed out"),
        ):
            result = sender.send(
                to="user@example.com",
                event_type=EventType.REPLY_RECEIVED,
                variables=reply_variables,
            )

        assert result is None

    def test_request_exception_returns_none_immediately(
        self,
        sender: EmailSender,
        reply_variables: dict[str, str],
    ) -> None:
        """A RequestException (DNS, connection refused) must return None.

        Transport failures are soft errors that the notification queue will
        retry. Propagating the exception would crash the cron job.
        """
        with patch(
            "requests.post",
            side_effect=req.RequestException("connection refused"),
        ):
            result = sender.send(
                to="user@example.com",
                event_type=EventType.REPLY_RECEIVED,
                variables=reply_variables,
            )

        assert result is None


# ---------------------------------------------------------------------------
# Response parsing
# ---------------------------------------------------------------------------


class TestResponseParsing:
    """Tests for success-response body handling."""

    def test_missing_id_field_returns_none(
        self,
        sender: EmailSender,
        reply_variables: dict[str, str],
    ) -> None:
        """A 200 response without an 'id' key must return None.

        The ID is required for delivery tracking. Returning a synthetic or
        empty string would store a useless identifier in the Notification
        record.
        """
        no_id = Mock()
        no_id.status_code = 200
        no_id.json.return_value = {}

        with patch(
            _PATCH_POST,
            return_value=no_id,
        ):
            result = sender.send(
                to="user@example.com",
                event_type=EventType.REPLY_RECEIVED,
                variables=reply_variables,
            )

        assert result is None

    def test_malformed_json_returns_none(
        self,
        sender: EmailSender,
        reply_variables: dict[str, str],
    ) -> None:
        """A 200 with a non-dict JSON body must return None.

        Resend should not return this, but defensive handling prevents an
        unhandled TypeError from crashing the cron job.
        """
        malformed = Mock()
        malformed.status_code = 200
        malformed.json.side_effect = ValueError("not valid json")

        with patch(
            _PATCH_POST,
            return_value=malformed,
        ):
            result = sender.send(
                to="user@example.com",
                event_type=EventType.REPLY_RECEIVED,
                variables=reply_variables,
            )

        assert result is None

    def test_non_dict_json_body_returns_none(
        self,
        sender: EmailSender,
        reply_variables: dict[str, str],
    ) -> None:
        """A 200 response whose JSON body is not a dict must return None.

        Subscripting a list or string with ["id"] raises TypeError. The
        except clause must catch TypeError to prevent the cron job crashing
        on an unexpected Resend API change.
        """
        non_dict = Mock()
        non_dict.status_code = 200
        non_dict.json.return_value = ["unexpected", "list"]

        with patch(_PATCH_POST, return_value=non_dict):
            result = sender.send(
                to="user@example.com",
                event_type=EventType.REPLY_RECEIVED,
                variables=reply_variables,
            )

        assert result is None


# ---------------------------------------------------------------------------
# Input validation
# ---------------------------------------------------------------------------


class TestInputValidation:
    """Tests for pre-send input validation."""

    def test_missing_at_sign_returns_none_without_posting(
        self,
        sender: EmailSender,
        reply_variables: dict[str, str],
    ) -> None:
        """An address without '@' must return None before any HTTP call.

        Resend would reject the address with a 422, but validating locally
        avoids a network round-trip and keeps the error log unambiguous.
        """
        with patch(_PATCH_POST) as mock_post:
            result = sender.send(
                to="notavalidemail",
                event_type=EventType.REPLY_RECEIVED,
                variables=reply_variables,
            )

        assert result is None
        mock_post.assert_not_called()


# ---------------------------------------------------------------------------
# Dependency injection factory
# ---------------------------------------------------------------------------


class TestGetEmailSenderDependency:
    """Tests for the get_email_sender dependency function."""

    def test_get_email_sender_returns_instance(self, test_env) -> None:
        """get_email_sender() must return an EmailSender instance.

        The factory is the sole construction path for route handlers.
        Returning any other type would break callers that rely on the
        EmailSender interface.
        """
        import backend.api.dependencies as deps

        deps._email_sender = None
        try:
            from backend.api.dependencies import get_email_sender

            service = get_email_sender()
            assert isinstance(service, EmailSender)
        finally:
            deps._email_sender = None

    def test_get_email_sender_is_singleton(self, test_env) -> None:
        """Two calls to get_email_sender() must return the same object.

        The sender is stateless and safe to share. A singleton avoids
        unnecessary object creation on every notification batch.
        """
        import backend.api.dependencies as deps

        deps._email_sender = None
        try:
            from backend.api.dependencies import get_email_sender

            first = get_email_sender()
            second = get_email_sender()
            assert first is second
        finally:
            deps._email_sender = None
