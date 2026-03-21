"""Resend email delivery service.

Provides HTTP-based email sending via the Resend API using the requests
library. Implements exponential backoff retry logic for rate limiting and
transient server errors.

Part of the Notification bounded context infrastructure layer.
"""

import logging
import time

import requests

logger = logging.getLogger(__name__)

_RESEND_EMAILS_URL = "https://api.resend.com/emails"


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


class ResendEmailService:
    """Send transactional emails via the Resend HTTP API.

    Wraps the Resend /emails endpoint with retry logic for 429 and 5xx
    responses. All failures are returned as None rather than raised so
    callers can delegate retry scheduling to the notification queue.

    Attributes:
        _api_key: Resend API key for bearer authentication.
        _domain: Sending domain (From address).
        _timeout: HTTP request timeout in seconds.
        _max_retries: Maximum retry attempts for retryable errors.
    """

    def __init__(
        self,
        api_key: str,
        domain: str = "noreply@example.com",
        timeout: int = 10,
        max_retries: int = 3,
    ) -> None:
        """Initialise the email service.

        Args:
            api_key: Resend API secret key.
            domain: Sender address used in the From field.
            timeout: Per-request timeout in seconds.
            max_retries: Maximum attempts before giving up on retryable errors.
        """
        self._api_key = api_key
        self._domain = domain
        self._timeout = timeout
        self._max_retries = max_retries

    def _post_with_retry(
        self, payload: dict[str, object], safe_to: str
    ) -> str | None:
        """POST payload to the Resend API with exponential backoff retry.

        Retries on 429 (rate limit) and 5xx (server error) responses.
        Returns None immediately on 4xx client errors, network timeouts,
        or after exhausting retries.

        Args:
            payload: JSON-serialisable request body for the Resend API.
            safe_to: Pre-redacted recipient string used only in log messages.

        Returns:
            The Resend email ID string on success, or None on failure.
        """
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
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
                logger.error("Timeout sending email to %s", safe_to)
                return None
            except requests.RequestException as exc:
                logger.error(
                    "Network error sending email to %s: %s", safe_to, exc
                )
                return None

            if response.status_code in (200, 201):
                try:
                    email_id: str = response.json()["id"]
                except (KeyError, ValueError):
                    logger.error(
                        "Missing 'id' in Resend response sending to %s", safe_to
                    )
                    return None
                logger.info("Email sent to %s, id=%s", safe_to, email_id)
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

    def send_email(
        self,
        to: str,
        subject: str,
        html: str,
    ) -> str | None:
        """Send an inline HTML email via the Resend API.

        Retries on 429 (rate limit) and 5xx (server error) responses with
        exponential backoff. Returns None immediately on 4xx client errors
        or network timeouts without retrying.

        Args:
            to: Recipient email address.
            subject: Email subject line.
            html: HTML email body content.

        Returns:
            The Resend email ID string on success, or None on failure.
        """
        payload: dict[str, object] = {
            "from": self._domain,
            "to": to,
            "subject": subject,
            "html": html,
        }
        return self._post_with_retry(payload, to)

    def send_template(
        self,
        to: str,
        template_id: str,
        variables: dict[str, str],
    ) -> str | None:
        """Send a template-based email via the Resend API.

        Validates the recipient address, builds the template payload, then
        delegates to _post_with_retry with a redacted address for logging.

        Args:
            to: Recipient email address (must contain '@').
            template_id: Resend template ID or alias to use for rendering.
            variables: Template variable key-value pairs for substitution.

        Returns:
            The Resend email ID string on success, or None on failure.
        """
        if "@" not in to:
            logger.error(
                "Invalid recipient address for template send: %s",
                _redact_email(to),
            )
            return None

        payload: dict[str, object] = {
            "from": self._domain,
            "to": to,
            "template_id": template_id,
            "variables": variables,
        }
        return self._post_with_retry(payload, _redact_email(to))
