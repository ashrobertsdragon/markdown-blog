"""Shared test fixtures for all database settings."""

import pytest

from backend.config import DBSettings, ProductionDBSettings


@pytest.fixture
def valid_env(clean_env):
    """Fixture to set environment variables."""
    clean_env.setenv("DB_NAME", "blog_db")
    clean_env.setenv("DB_USER", "blog_user")
    clean_env.setenv("DB_PASSWORD", "secure_password")
    return clean_env


@pytest.fixture
def base_settings(valid_env) -> DBSettings:
    """Fixture to initialize base DBSettings class."""
    return DBSettings()


@pytest.fixture
def production_env(clean_env):
    """Fixture to initialize ProductionDBSettings environment variables."""
    clean_env.setenv("FLASK_ENV", "PRODUCTION")
    clean_env.setenv("DB_NAME", "PRODUCTION_DB")
    clean_env.setenv("DB_USER", "PRODUCTION_USER")
    clean_env.setenv("DB_PASSWORD", "PRODUCTION_PASSWORD")
    return clean_env


@pytest.fixture
def production_settings(production_env) -> ProductionDBSettings:
    """Fixture to initialize ProductionDBSettings class."""
    return ProductionDBSettings()
