"""Query and result types for the GetSystemHealth use case."""

from dataclasses import dataclass


@dataclass(frozen=True)
class GetSystemHealthQuery:
    """Query requesting a snapshot of current system health.

    Sentinel value object — carries no input parameters.
    """


@dataclass(frozen=True)
class SystemHealth:
    """Health snapshot returned by get_system_health_query_handler."""

    status: str
    database: str
    filesystem: str
    github_api: str
    uptime_seconds: int
    checked_at: str
