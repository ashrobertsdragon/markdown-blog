"""Template-based email sender for the Notification bounded context.

Sends transactional emails by composing ResendEmailService rather than
duplicating HTTP logic. Resolves EventType to a Resend template alias and
delegates delivery to ResendEmailService.send_template.

Part of the Notification bounded context infrastructure layer.
"""

import logging

from backend.domain.aggregates.notification import EventType
from backend.infrastructure.email.email_templates import (
    TEMPLATE_REPLY_NOTIFICATION,
)
from backend.infrastructure.email.resend_email_service import ResendEmailService

logger = logging.getLogger(__name__)

_DEFAULT_TEMPLATE_MAP: dict[EventType, str] = {
    EventType.REPLY_RECEIVED: TEMPLATE_REPLY_NOTIFICATION,
    EventType.COMMENT_POSTED: TEMPLATE_REPLY_NOTIFICATION,
}


def _redact_email(address: str) -> str:
    """Return only the domain portion of an email address for safe logging.

    Avoids storing recipient PII in structured logs while still providing
    enough context to correlate delivery failures by domain.

    Args:
        address: A full email address string.

    Returns:
        The '@domain' suffix if '@' is present, otherwise '(invalid)'.
    """
    at = address.find("@")
    if at == -1:
        return "(invalid)"
    return address[at:]


class EmailSender:
    """Send transactional emails via Resend's template-based API.

    Composes ResendEmailService for HTTP delivery. Resolves EventType to a
    template alias and delegates to send_template. Returns None on failure
    so callers can delegate retry to the notification queue.

    Attributes:
        _service: ResendEmailService instance used for delivery.
        _template_map: Mapping from EventType to Resend template alias.
    """

    def __init__(
        self,
        service: ResendEmailService,
        template_map: dict[EventType, str] | None = None,
    ) -> None:
        """Initialise the email sender.

        Args:
            service: ResendEmailService instance for HTTP delivery.
            template_map: Optional override for EventType → template alias
                mapping. Defaults to the built-in map when omitted.
        """
        self._service = service
        self._template_map = (
            template_map if template_map is not None else _DEFAULT_TEMPLATE_MAP
        )

    def send(
        self,
        to: str,
        event_type: EventType,
        variables: dict[str, str],
    ) -> str | None:
        """Send an email using a Resend template.

        Validates the recipient address format, resolves the template alias
        from event_type, then delegates to ResendEmailService.send_template.
        Returns None immediately on invalid address. Raises ValueError for
        unmapped event types before any network call.

        Args:
            to: Recipient email address (must contain '@').
            event_type: Domain event type used to select the template.
            variables: Template variable key-value pairs for substitution.

        Returns:
            The Resend email ID string on success, or None on failure.
        """
        if "@" not in to:
            logger.error(
                "Invalid recipient address format: %s",
                _redact_email(to),
            )
            return None

        template_alias = self._resolve_template_alias(event_type)
        return self._service.send_template(
            to=to,
            template_id=template_alias,
            variables=variables,
        )

    def _resolve_template_alias(self, event_type: EventType) -> str:
        """Return the Resend template alias for the given event type.

        Args:
            event_type: The domain event that triggered the notification.

        Returns:
            The Resend template alias string.

        Raises:
            ValueError: If event_type is not in the template map.
        """
        alias = self._template_map.get(event_type)
        if alias is None:
            raise ValueError(
                f"No template configured for event type '{event_type}'"
            )
        return alias
