"""Resend email template management service.

Provides CRUD operations for Resend email templates via the Resend HTTP API
using the requests library. Used by provisioning scripts to register and
publish templates before email dispatch begins.

Part of the Notification bounded context infrastructure layer.
"""

import logging
import urllib.parse

import requests

logger = logging.getLogger(__name__)

_RESEND_TEMPLATES_URL = "https://api.resend.com/templates"


class ResendTemplateManager:
    """Manage email templates in the Resend template registry.

    Provides create, publish, get, and delete operations against the Resend
    templates API. Raises on conflict (409) so provisioning scripts can
    detect duplicate aliases explicitly. Returns None or False on transient
    server errors rather than raising.

    Attributes:
        _api_key: Resend API key for bearer authentication.
        _timeout: HTTP request timeout in seconds.
    """

    def __init__(self, api_key: str, timeout: int = 10) -> None:
        """Initialise the template manager.

        Args:
            api_key: Resend API secret key.
            timeout: Per-request timeout in seconds.
        """
        self._api_key = api_key
        self._timeout = timeout

    @property
    def _headers(self) -> dict[str, str]:
        """Build standard auth headers for all requests."""
        return {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }

    def create_template(
        self,
        name: str,
        alias: str,
        subject: str,
        html: str,
    ) -> str | None:
        """Create a new email template in the Resend registry.

        Args:
            name: Human-readable template name.
            alias: Stable slug identifier for the template.
            subject: Email subject line (may use triple-mustache variables).
            html: HTML body (must use triple-mustache for variable
                substitution).

        Returns:
            The new template ID string on success, or None on 5xx error.

        Raises:
            ValueError: If the alias already exists (409 Conflict).
        """
        payload = {
            "name": name,
            "alias": alias,
            "subject": subject,
            "html": html,
        }

        try:
            response = requests.post(
                _RESEND_TEMPLATES_URL,
                json=payload,
                headers=self._headers,
                timeout=self._timeout,
            )
        except requests.Timeout:
            logger.error("Timeout creating template '%s'", alias)
            return None
        except requests.RequestException as exc:
            logger.error("Network error creating template '%s': %s", alias, exc)
            return None

        if response.status_code == 409:
            logger.warning("Template alias '%s' already exists", alias)
            raise ValueError(f"Template alias '{alias}' already exists")

        if response.status_code >= 500:
            logger.error(
                "Server error %d creating template '%s'",
                response.status_code,
                alias,
            )
            return None

        if response.status_code in (200, 201):
            try:
                template_id: str = response.json()["id"]
            except (KeyError, ValueError):
                logger.error(
                    "Missing 'id' in Resend response creating template '%s'",
                    alias,
                )
                return None
            logger.info("Created template '%s' with id=%s", alias, template_id)
            return template_id

        logger.error(
            "Unexpected status %d creating template '%s'",
            response.status_code,
            alias,
        )
        return None

    def publish_template(self, template_id: str) -> bool:
        """Publish an existing template to make it active for delivery.

        Args:
            template_id: The Resend template ID returned by create_template.

        Returns:
            True on success, False if the template was not found (404) or on
            network/server error.
        """
        encoded_id = urllib.parse.quote(template_id, safe="")
        url = f"{_RESEND_TEMPLATES_URL}/{encoded_id}/publish"

        try:
            response = requests.post(
                url,
                headers=self._headers,
                timeout=self._timeout,
            )
        except requests.Timeout:
            logger.error("Timeout publishing template %s", template_id)
            return False
        except requests.RequestException as exc:
            logger.error(
                "Network error publishing template %s: %s", template_id, exc
            )
            return False

        if response.status_code == 200:
            logger.info("Published template %s", template_id)
            return True

        if response.status_code == 404:
            logger.warning("Template %s not found for publish", template_id)
            return False

        logger.error(
            "Unexpected status %d publishing template %s",
            response.status_code,
            template_id,
        )
        return False

    def get_template(self, template_id_or_alias: str) -> dict | None:
        """Retrieve a template by ID or alias.

        Args:
            template_id_or_alias: The Resend template ID or alias string.

        Returns:
            A dict containing at minimum 'id' and 'alias', or None if not found
            or on network/server error.
        """
        encoded = urllib.parse.quote(template_id_or_alias, safe="")
        url = f"{_RESEND_TEMPLATES_URL}/{encoded}"

        try:
            response = requests.get(
                url,
                headers=self._headers,
                timeout=self._timeout,
            )
        except requests.Timeout:
            logger.error("Timeout fetching template '%s'", template_id_or_alias)
            return None
        except requests.RequestException as exc:
            logger.error(
                "Network error fetching template '%s': %s",
                template_id_or_alias,
                exc,
            )
            return None

        if response.status_code == 200:
            data: dict = response.json()
            return data

        if response.status_code == 404:
            logger.warning("Template '%s' not found", template_id_or_alias)
            return None

        logger.error(
            "Unexpected status %d fetching template '%s'",
            response.status_code,
            template_id_or_alias,
        )
        return None

    def delete_template(self, template_id: str) -> bool:
        """Delete a template from the Resend registry.

        Args:
            template_id: The Resend template ID to delete.

        Returns:
            True on successful deletion, False otherwise.
        """
        encoded_id = urllib.parse.quote(template_id, safe="")
        url = f"{_RESEND_TEMPLATES_URL}/{encoded_id}"

        try:
            response = requests.delete(
                url,
                headers=self._headers,
                timeout=self._timeout,
            )
        except requests.Timeout:
            logger.error("Timeout deleting template %s", template_id)
            return False
        except requests.RequestException as exc:
            logger.error(
                "Network error deleting template %s: %s", template_id, exc
            )
            return False

        if response.status_code == 200:
            logger.info("Deleted template %s", template_id)
            return True

        logger.error(
            "Unexpected status %d deleting template %s",
            response.status_code,
            template_id,
        )
        return False
