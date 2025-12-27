"""Unit tests for ProductionDBSettings environment variable prefix.

These tests verify that ProductionDBSettings reads from standard environment
variable names (DB_HOST, DB_NAME, DB_USER, DB_PASSWORD) instead of requiring
a CPANEL_ prefix. This aligns with Passenger WSGI's standard environment setup.
"""

import pytest
from pydantic import ValidationError

from backend.config import ProductionDBSettings, _db_settings, get_db_url


def test_production_settings_reads_standard_db_env_vars(clean_env):
    """ProductionDBSettings reads standard DB_* environment variables.

    Verifies that DB_HOST, DB_NAME, DB_USER, DB_PASSWORD are read
    directly without requiring a CPANEL_ prefix.
    """
    clean_env.setenv("DB_HOST", "localhost")
    clean_env.setenv("DB_NAME", "test_db")
    clean_env.setenv("DB_USER", "test_user")
    clean_env.setenv("DB_PASSWORD", "test_pass")
    clean_env.setenv("FLASK_ENV", "PRODUCTION")

    settings = ProductionDBSettings()

    assert settings.DB_HOST == "localhost"
    assert settings.DB_NAME == "test_db"
    assert settings.DB_USER == "test_user"
    assert settings.DB_PASSWORD == "test_pass"


def test_production_settings_ignores_cpanel_prefix(clean_env):
    """ProductionDBSettings uses DB_* values, not CPANEL_DB_* values.

    When both standard (DB_*) and prefixed (CPANEL_DB_*) variables
    exist, verify that standard variables take precedence.
    """
    clean_env.setenv("DB_HOST", "standard_host")
    clean_env.setenv("DB_NAME", "standard_db")
    clean_env.setenv("DB_USER", "standard_user")
    clean_env.setenv("DB_PASSWORD", "standard_pass")

    clean_env.setenv("CPANEL_DB_HOST", "prefixed_host")
    clean_env.setenv("CPANEL_DB_NAME", "prefixed_db")
    clean_env.setenv("CPANEL_DB_USER", "prefixed_user")
    clean_env.setenv("CPANEL_DB_PASSWORD", "prefixed_pass")

    clean_env.setenv("FLASK_ENV", "PRODUCTION")

    settings = ProductionDBSettings()

    assert settings.DB_HOST == "standard_host"
    assert settings.DB_NAME == "standard_db"
    assert settings.DB_USER == "standard_user"
    assert settings.DB_PASSWORD == "standard_pass"


def test_production_url_constructed_from_standard_env_vars(clean_env):
    """get_db_url constructs URL from standard environment variables.

    Verifies the complete integration: standard env vars ->
    ProductionDBSettings -> correct PostgreSQL connection URL.
    """
    clean_env.setenv("DB_HOST", "localhost")
    clean_env.setenv("DB_NAME", "test_db")
    clean_env.setenv("DB_USER", "test_user")
    clean_env.setenv("DB_PASSWORD", "test_pass")
    clean_env.setenv("FLASK_ENV", "PRODUCTION")

    get_db_url.cache_clear()
    _db_settings.cache_clear()

    url = get_db_url()
    expected_url = "postgresql+psycopg2://test_user:test_pass@localhost/test_db"

    assert url == expected_url


def test_production_settings_fails_without_standard_env_vars(clean_env):
    """ProductionDBSettings raises ValidationError without DB_* variables.

    When only CPANEL_* prefixed variables are set (not DB_*), verify
    that ProductionDBSettings fails validation, confirming it expects
    standard variable names.
    """
    clean_env.setenv("CPANEL_DB_HOST", "prefixed_host")
    clean_env.setenv("CPANEL_DB_NAME", "prefixed_db")
    clean_env.setenv("CPANEL_DB_USER", "prefixed_user")
    clean_env.setenv("CPANEL_DB_PASSWORD", "prefixed_pass")
    clean_env.setenv("FLASK_ENV", "PRODUCTION")

    with pytest.raises(ValidationError) as exc_info:
        ProductionDBSettings()

    error_str = str(exc_info.value)
    assert (
        "DB_NAME" in error_str
        or "DB_USER" in error_str
        or "DB_PASSWORD" in error_str
    )
