from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration, read from environment variables."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str
    """SQLAlchemy URL, e.g. ``postgresql+psycopg://user:pass@db:5432/tracker``."""


@lru_cache
def get_settings() -> Settings:
    return Settings()
