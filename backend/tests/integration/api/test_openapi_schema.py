"""Integration tests asserting notification endpoints are documented in openapi.yaml."""

from pathlib import Path
from typing import Any

import yaml

OPENAPI_PATH = (
    Path(__file__).parent.parent.parent.parent.parent
    / "shared"
    / "openapi.yaml"
)


def _load_spec() -> dict[str, Any]:
    """Load and parse the OpenAPI YAML spec."""
    with OPENAPI_PATH.open() as f:
        data: dict[str, Any] = yaml.safe_load(f)
        return data


class TestNotificationPathsExist:
    """Assert notification API paths are present in the spec."""

    def test_user_notification_preferences_get_exists(self) -> None:
        """GET /user/notification-preferences must be documented."""
        spec = _load_spec()
        paths = spec.get("paths", {})
        assert "/user/notification-preferences" in paths, (
            "Path /user/notification-preferences missing from openapi.yaml"
        )
        operations = paths["/user/notification-preferences"]
        assert "get" in operations, (
            "GET operation missing from /user/notification-preferences"
        )

    def test_user_notification_preferences_put_exists(self) -> None:
        """PUT /user/notification-preferences must be documented."""
        spec = _load_spec()
        paths = spec.get("paths", {})
        assert "/user/notification-preferences" in paths, (
            "Path /user/notification-preferences missing from openapi.yaml"
        )
        operations = paths["/user/notification-preferences"]
        assert "put" in operations, (
            "PUT operation missing from /user/notification-preferences"
        )

    def test_admin_notifications_get_exists(self) -> None:
        """GET /admin/notifications must be documented."""
        spec = _load_spec()
        paths = spec.get("paths", {})
        assert "/admin/notifications" in paths, (
            "Path /admin/notifications missing from openapi.yaml"
        )
        operations = paths["/admin/notifications"]
        assert "get" in operations, (
            "GET operation missing from /admin/notifications"
        )

    def test_unsubscribe_get_exists(self) -> None:
        """GET /unsubscribe must be documented."""
        spec = _load_spec()
        paths = spec.get("paths", {})
        assert "/unsubscribe" in paths, (
            "Path /unsubscribe missing from openapi.yaml"
        )
        operations = paths["/unsubscribe"]
        assert "get" in operations, "GET operation missing from /unsubscribe"


class TestNotificationSchemasExist:
    """Assert all notification-related component schemas are defined."""

    def _schemas(self) -> dict[str, Any]:
        spec = _load_spec()
        components: dict[str, Any] = spec.get("components", {})
        schemas: dict[str, Any] = components.get("schemas", {})
        return schemas

    def test_notification_preferences_response_schema_exists(self) -> None:
        """NotificationPreferencesResponse schema must be defined."""
        assert "NotificationPreferencesResponse" in self._schemas(), (
            "NotificationPreferencesResponse missing from components/schemas"
        )

    def test_notification_preferences_request_schema_exists(self) -> None:
        """NotificationPreferencesRequest schema must be defined."""
        assert "NotificationPreferencesRequest" in self._schemas(), (
            "NotificationPreferencesRequest missing from components/schemas"
        )

    def test_notification_list_response_schema_exists(self) -> None:
        """NotificationListResponse schema must be defined."""
        assert "NotificationListResponse" in self._schemas(), (
            "NotificationListResponse missing from components/schemas"
        )

    def test_notification_item_schema_exists(self) -> None:
        """NotificationItem schema must be defined."""
        assert "NotificationItem" in self._schemas(), (
            "NotificationItem missing from components/schemas"
        )

    def test_unsubscribe_response_schema_exists(self) -> None:
        """UnsubscribeResponse schema must be defined."""
        assert "UnsubscribeResponse" in self._schemas(), (
            "UnsubscribeResponse missing from components/schemas"
        )


class TestNotificationSecurityRequirements:
    """Assert security declarations are correct on each notification endpoint."""

    def _operation(self, path: str, method: str) -> dict[str, Any]:
        spec = _load_spec()
        operation: dict[str, Any] = spec["paths"][path][method]
        return operation

    def test_get_preferences_requires_bearer_auth(self) -> None:
        """GET /user/notification-preferences must require bearerAuth."""
        operation = self._operation("/user/notification-preferences", "get")
        security = operation.get("security", [])
        bearer_entries = [s for s in security if "bearerAuth" in s]
        assert bearer_entries, (
            "GET /user/notification-preferences must declare bearerAuth security"
        )

    def test_put_preferences_requires_bearer_auth(self) -> None:
        """PUT /user/notification-preferences must require bearerAuth."""
        operation = self._operation("/user/notification-preferences", "put")
        security = operation.get("security", [])
        bearer_entries = [s for s in security if "bearerAuth" in s]
        assert bearer_entries, (
            "PUT /user/notification-preferences must declare bearerAuth security"
        )

    def test_admin_notifications_requires_bearer_auth(self) -> None:
        """GET /admin/notifications must require bearerAuth."""
        operation = self._operation("/admin/notifications", "get")
        security = operation.get("security", [])
        bearer_entries = [s for s in security if "bearerAuth" in s]
        assert bearer_entries, (
            "GET /admin/notifications must declare bearerAuth security"
        )

    def test_unsubscribe_is_public(self) -> None:
        """GET /unsubscribe must have empty security list (public endpoint)."""
        operation = self._operation("/unsubscribe", "get")
        assert "security" in operation, (
            "GET /unsubscribe must have an explicit security field"
        )
        assert operation["security"] == [], (
            "GET /unsubscribe must set security: [] to override global bearerAuth"
        )


class TestNotificationsTagExists:
    """Assert the Notifications tag is declared in the spec tags section."""

    def test_notifications_tag_declared(self) -> None:
        """The spec must include a Notifications tag entry."""
        spec = _load_spec()
        tags = spec.get("tags", [])
        tag_names = [t.get("name") for t in tags]
        assert "Notifications" in tag_names, (
            f"'Notifications' tag missing from spec tags section; found: {tag_names}"
        )
