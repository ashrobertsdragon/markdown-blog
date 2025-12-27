"""Application configuration management."""

import os
from enum import StrEnum
from functools import lru_cache
from pathlib import Path
from typing import ClassVar

from pydantic import Field, PostgresDsn
from pydantic_settings import BaseSettings, SettingsConfigDict


class FlaskEnv(StrEnum):
    """Enum for Flask environment setting."""

    PRODUCTION = "PRODUCTION"
    DEVELOPMENT = "DEVELOPMENT"
    TESTING = "TESTING"


class FlaskSettings(BaseSettings):
    """Flask settings.

    PARAMETERS:
        FLASK_ENV (FlaskEnv[Enum]): The Flask environment type.
        BUILD_DIR (Path): The path to the build directory.
        STATIC_DIR (Path): The path to the static directory.
    """

    model_config = SettingsConfigDict(env_parse_enums=True)

    FLASK_ENV: FlaskEnv = Field(
        default=FlaskEnv.PRODUCTION, validation_alias="FLASK_ENV"
    )
    BUILD_DIR: Path = Field(
        default=Path(__file__).parents[3] / "build",
        validation_alias="BUILD_DIR",
    )
    STATIC_PATH: Path | None = Field(
        default=None, validation_alias="STATIC_PATH"
    )

    @property
    def STATIC_DIR(self) -> str:
        """Path to static directory."""
        if self.STATIC_PATH:
            return str(self.STATIC_PATH)
        return str(self.BUILD_DIR / "static")


class DBSettings(BaseSettings):
    """Base settings class.

    PARAMETERS:
        DB_HOST (str): `localhost`.
        DB_NAME (str): The database name.
        DB_USER (str): The database username.
        DB_PASSWORD (str): The database password.
        FLASK_ENV (FlaskEnv[Enum]): The Flask environment type.
    """

    _registry: ClassVar[dict[FlaskEnv, type["DBSettings"]]] = {}
    model_config = SettingsConfigDict(env_parse_enums=True)

    DB_HOST: str = Field(default="localhost", validation_alias="DB_HOST")
    DB_NAME: str = Field(default=...)
    DB_USER: str = Field(default=...)
    DB_PASSWORD: str = Field(default=...)
    FLASK_ENV: FlaskEnv = Field(
        default=FlaskEnv.PRODUCTION, validation_alias="FLASK_ENV"
    )

    def __init_subclass__(cls, **kwargs) -> None:
        """Register subclasses based on FLASK_ENV value."""
        super().__init_subclass__(**kwargs)
        DBSettings._registry[cls.FLASK_ENV] = cls

    @property
    def url(self) -> str:
        """Database connection string."""
        db: PostgresDsn = PostgresDsn(
            f"postgresql+psycopg2://{self.DB_USER}:{self.DB_PASSWORD}"
            f"@{self.DB_HOST}/{self.DB_NAME}"
        )
        return str(db)


class TestDBSettings(DBSettings):
    """Settings for testing."""

    model_config = SettingsConfigDict(env_prefix="LOCAL_")
    FLASK_ENV: FlaskEnv = FlaskEnv.TESTING


class DevDBSettings(DBSettings):
    """Settings for development."""

    model_config = SettingsConfigDict(env_prefix="LOCAL_")
    FLASK_ENV: FlaskEnv = FlaskEnv.DEVELOPMENT


class ProductionDBSettings(DBSettings):
    """Settings for production."""

    model_config = SettingsConfigDict(env_prefix="")
    FLASK_ENV: FlaskEnv = FlaskEnv.PRODUCTION


@lru_cache
def _db_settings(flask_env: str | None = None) -> DBSettings:
    """Factory function for initializing DBSettings subclass from FLASK_ENV."""
    try:
        env = flask_env or os.environ["FLASK_ENV"]
        settings_class = DBSettings._registry[FlaskEnv[env]]
        return settings_class()
    except KeyError:
        return ProductionDBSettings()


@lru_cache
def get_db_url() -> str:
    """Database connection string.

    Returns:
        str: Validated database connection string based on envars.
    """
    return _db_settings().url
