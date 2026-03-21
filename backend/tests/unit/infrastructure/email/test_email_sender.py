"""Unit tests for EmailSender.

Covers:
- Template alias resolution: EventType → Resend template alias
- Successful send delegates to ResendEmailService.send_template
- send_template returns email ID → send() returns it
- send_template returns None → send() returns None
- Unknown EventType raises ValueError before calling service
- Invalid email (no '@') returns None without calling service
- send() passes the resolved alias and variables to send_template
"""

from unittest.mock import patch

import pytest

from backend.domain.aggregates.notification import EventType
from backend.infrastructure.email.email_sender import EmailSender
from backend.infrastructure.email.resend_email_service import ResendEmailService

_PATCH_SEND_TEMPLATE = "backend.infrastructure.email.resend_email_service.ResendEmailService.send_template"

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def sender() -> EmailSender:
    """EmailSender composed with a ResendEmailService instance."""
    return EmailSender(service=ResendEmailService(api_key="re_test_key"))  # type: ignore[call-arg]


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
        custom_sender = EmailSender(  # type: ignore[missing-argument]
            service=ResendEmailService(api_key="re_test"),  # type: ignore[unknown-argument]
            template_map=custom,
        )
        assert (
            custom_sender._resolve_template_alias(EventType.REPLY_RECEIVED)
            == "custom-reply-template"
        )

    def test_unknown_event_type_raises_value_error(
        self, sender: EmailSender
    ) -> None:
        """An EventType absent from the template map must raise ValueError.

        Unmapped event types indicate a programming error: a new EventType
        was added without a corresponding template alias. Failing loudly
        prevents silent no-ops where a notification is swallowed without
        delivery.
        """
        with pytest.raises(ValueError, match="No template configured"):
            sender._resolve_template_alias(EventType.MENTION)


# ---------------------------------------------------------------------------
# Delegation to ResendEmailService.send_template
# ---------------------------------------------------------------------------


class TestSuccessfulSend:
    """Tests for the happy-path send flow delegating to send_template."""

    def test_send_returns_email_id_when_send_template_succeeds(
        self,
        sender: EmailSender,
        reply_variables: dict[str, str],
    ) -> None:
        """send() must return the ID that send_template returns on success.

        The email ID is stored on the Notification record for delivery
        tracking and admin debugging via the Resend dashboard.
        """
        with patch(_PATCH_SEND_TEMPLATE, return_value="email_abc123"):
            result = sender.send(
                to="user@example.com",
                event_type=EventType.REPLY_RECEIVED,
                variables=reply_variables,
            )

        assert result == "email_abc123"

    def test_send_passes_resolved_alias_to_send_template(
        self,
        sender: EmailSender,
        reply_variables: dict[str, str],
    ) -> None:
        """send() must pass the resolved template alias to send_template.

        The alias comes from _resolve_template_alias; it must reach
        send_template unchanged so Resend routes to the correct template.
        """
        with patch(
            _PATCH_SEND_TEMPLATE, return_value="email_abc123"
        ) as mock_st:
            sender.send(
                to="user@example.com",
                event_type=EventType.REPLY_RECEIVED,
                variables=reply_variables,
            )

        _, kwargs = mock_st.call_args
        assert kwargs.get("template_id") == "reply-notification" or (
            mock_st.call_args[0][1] == "reply-notification"
        )

    def test_send_passes_variables_to_send_template(
        self,
        sender: EmailSender,
        reply_variables: dict[str, str],
    ) -> None:
        """send() must forward the variables dict to send_template verbatim.

        Without variables the template renders with empty placeholders,
        producing emails with blank author names, post titles, and URLs.
        """
        with patch(
            _PATCH_SEND_TEMPLATE, return_value="email_abc123"
        ) as mock_st:
            sender.send(
                to="user@example.com",
                event_type=EventType.REPLY_RECEIVED,
                variables=reply_variables,
            )

        call_kwargs = mock_st.call_args[1]
        passed_variables = call_kwargs.get(
            "variables",
            mock_st.call_args[0][2] if len(mock_st.call_args[0]) > 2 else None,
        )
        assert passed_variables == reply_variables

    def test_send_passes_recipient_to_send_template(
        self,
        sender: EmailSender,
        reply_variables: dict[str, str],
    ) -> None:
        """send() must forward the recipient address to send_template.

        Passing the wrong address — or omitting it — would silently deliver
        the email to the wrong recipient or no recipient at all.
        """
        with patch(
            _PATCH_SEND_TEMPLATE, return_value="email_abc123"
        ) as mock_st:
            sender.send(
                to="recipient@example.com",
                event_type=EventType.REPLY_RECEIVED,
                variables=reply_variables,
            )

        call_args = mock_st.call_args
        passed_to = call_args[1].get("to") or call_args[0][0]
        assert passed_to == "recipient@example.com"

    def test_send_template_returning_none_propagates_as_none(
        self,
        sender: EmailSender,
        reply_variables: dict[str, str],
    ) -> None:
        """When send_template returns None, send() must also return None.

        None signals delivery failure to the notification processor so it
        can schedule a retry via the queue rather than marking the
        notification as delivered.
        """
        with patch(_PATCH_SEND_TEMPLATE, return_value=None):
            result = sender.send(
                to="user@example.com",
                event_type=EventType.REPLY_RECEIVED,
                variables=reply_variables,
            )

        assert result is None


# ---------------------------------------------------------------------------
# Input validation (before delegating to service)
# ---------------------------------------------------------------------------


class TestInputValidation:
    """Tests for pre-send validation that runs before calling the service."""

    def test_missing_at_sign_returns_none_without_calling_service(
        self,
        sender: EmailSender,
        reply_variables: dict[str, str],
    ) -> None:
        """An address without '@' must return None before any service call.

        Resend would reject the address with a 422, but validating locally
        avoids a network round-trip and keeps the error log unambiguous.
        """
        with patch(_PATCH_SEND_TEMPLATE) as mock_st:
            result = sender.send(
                to="notavalidemail",
                event_type=EventType.REPLY_RECEIVED,
                variables=reply_variables,
            )

        assert result is None
        mock_st.assert_not_called()

    def test_unknown_event_type_raises_before_calling_service(
        self,
        sender: EmailSender,
        reply_variables: dict[str, str],
    ) -> None:
        """An unmapped EventType must raise ValueError without calling send_template.

        Allowing an unknown type to reach send_template would silently pass
        a garbage alias to Resend, making the failure harder to diagnose.
        """
        with patch(_PATCH_SEND_TEMPLATE) as mock_st:
            with pytest.raises(ValueError):
                sender.send(
                    to="user@example.com",
                    event_type=EventType.MENTION,
                    variables=reply_variables,
                )

        mock_st.assert_not_called()


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
