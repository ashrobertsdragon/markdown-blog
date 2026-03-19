"""Template-based email sender for the Notification bounded context.

Sends transactional emails via the Resend Templates API using template IDs
(not inline HTML). Implements exponential backoff retry logic for rate
limiting and transient server errors. Treats 4xx client errors as permanent
failures.

Part of the Notification bounded context infrastructure layer.
"""

import logging
import time

import requests

from backend.domain.aggregates.notification import EventType
from backend.infrastructure.email.email_templates import (
    TEMPLATE_REPLY_NOTIFICATION,
)

logger = logging.getLogger(__name__)

_RESEND_EMAILS_URL = "https://api.resend.com/emails"

_DEFAULT_TEMPLATE_MAP: dict[EventType, str] = {
    # Both event types use the reply template; COMMENT_POSTED notifies the
    # post author in the same reply-style format as REPLY_RECEIVED.
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

    Uses template IDs (or aliases) and variable substitution rather than
    inline HTML. Implements exponential backoff for 429 and 5xx responses.
    Returns None on failure so callers can delegate retry to the notification
    queue rather than propagating exceptions.

    Attributes:
        _api_key: Resend API key for bearer authentication.
        _domain: Sender address used in the From field.
        _timeout: HTTP request timeout in seconds.
        _max_retries: Maximum retry attempts for retryable errors.
        _template_map: Mapping from EventType to Resend template alias.
    """

    def __init__(
        self,
        api_key: str,
        domain: str = "noreply@example.com",
        timeout: int = 10,
        max_retries: int = 3,
        template_map: dict[EventType, str] | None = None,
    ) -> None:
        """Initialise the email sender.

        Args:
            api_key: Resend API secret key.
            domain: Sender address used in the From field.
            timeout: Per-request timeout in seconds.
            max_retries: Maximum attempts before giving up on retryable errors.
            template_map: Optional override for EventType → template alias
                mapping. Defaults to the built-in map when omitted.
        """
        self._api_key = api_key
        self._domain = domain
        self._timeout = timeout
        self._max_retries = max_retries
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
        from event_type, then POSTs to Resend with the template and variable
        map. Retries on 429 and 5xx with exponential backoff. Returns None
        immediately on invalid address, 4xx, timeouts, or network errors.

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
        safe_to = _redact_email(to)
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "from": self._domain,
            "to": to,
            "template_id": template_alias,
            "variables": variables,
        }

        for attempt in range(self._max_retries + 1):
            try:
                response = requests.post(
                    _RESEND_EMAILS_URL,
                    json=payload,
                    headers=headers,
                    timeout=self._timeout,
                )
            except requests.Timeout:
                logger.error("Timeout sending template email to %s", safe_to)
                return None
            except requests.RequestException as exc:
                logger.error(
                    "Network error sending template email to %s: %s",
                    safe_to,
                    exc,
                )
                return None

            if response.status_code in (200, 201):
                try:
                    email_id: str = response.json()["id"]
                except (KeyError, ValueError, TypeError):
                    logger.error(
                        "Missing 'id' in Resend response sending to %s",
                        safe_to,
                    )
                    return None
                logger.info(
                    "Template email sent to %s via '%s', id=%s",
                    safe_to,
                    template_alias,
                    email_id,
                )
                return email_id

            if response.status_code == 429:
                delay = 2**attempt
                logger.warning(
                    "Rate limited sending to %s, retry %d/%d after %ds",
                    safe_to,
                    attempt + 1,
                    self._max_retries,
                    delay,
                )
                time.sleep(delay)
                continue

            if response.status_code >= 500:
                delay = 2**attempt
                logger.warning(
                    "Server error %d sending to %s, retry %d/%d after %ds",
                    response.status_code,
                    safe_to,
                    attempt + 1,
                    self._max_retries,
                    delay,
                )
                time.sleep(delay)
                continue

            logger.error(
                "Permanent failure sending to %s: HTTP %d",
                safe_to,
                response.status_code,
            )
            return None

        logger.error(
            "Exhausted %d retry attempts sending to %s",
            self._max_retries,
            safe_to,
        )
        return None

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
