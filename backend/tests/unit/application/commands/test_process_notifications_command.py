"""Unit tests for ProcessNotificationsCommand.

Covers:
- Default batch_limit=100, max_retries=3
- Custom values set correctly
- batch_limit <= 0 raises ValueError
- max_retries < 0 raises ValueError
- Frozen dataclass prevents mutation
"""

import pytest

from backend.application.commands.process_notifications_command import (
    ProcessNotificationsCommand,
)


def test_default_values() -> None:
    """Default batch_limit=100 and max_retries=3 are applied."""
    cmd = ProcessNotificationsCommand()

    assert cmd.batch_limit == 100
    assert cmd.max_retries == 3


def test_custom_values_set_correctly() -> None:
    """Custom batch_limit and max_retries are stored as given."""
    cmd = ProcessNotificationsCommand(batch_limit=50, max_retries=5)

    assert cmd.batch_limit == 50
    assert cmd.max_retries == 5


def test_rejects_zero_batch_limit() -> None:
    """batch_limit=0 raises ValueError."""
    with pytest.raises(ValueError, match="batch_limit"):
        ProcessNotificationsCommand(batch_limit=0)


def test_rejects_negative_batch_limit() -> None:
    """Negative batch_limit raises ValueError."""
    with pytest.raises(ValueError, match="batch_limit"):
        ProcessNotificationsCommand(batch_limit=-1)


def test_rejects_negative_max_retries() -> None:
    """Negative max_retries raises ValueError."""
    with pytest.raises(ValueError, match="max_retries"):
        ProcessNotificationsCommand(max_retries=-1)


def test_accepts_zero_max_retries() -> None:
    """max_retries=0 is valid (no retries, fail immediately)."""
    cmd = ProcessNotificationsCommand(max_retries=0)

    assert cmd.max_retries == 0


def test_command_is_frozen() -> None:
    """Frozen dataclass prevents attribute mutation."""
    cmd = ProcessNotificationsCommand()

    with pytest.raises((AttributeError, TypeError)):
        setattr(cmd, "batch_limit", 999)
