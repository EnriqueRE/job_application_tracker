"""The Alembic baseline builds the domain schema on an empty Postgres and tears it down."""

import os
from collections.abc import Iterator
from pathlib import Path
from uuid import uuid4

import pytest
from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.config import Config
from alembic.migration import MigrationContext
from sqlalchemy import Engine, create_engine, inspect, text
from sqlalchemy.engine import make_url

# Register every table on Base.metadata: the domain models and the import mapping.
import tracker.domain
import tracker.import_jobtrack.mapping  # noqa: F401
from tracker.db import Base
from tracker.settings import get_settings

BACKEND_DIR = Path(__file__).resolve().parent.parent
DOMAIN_TABLES = {"organizations", "applications", "application_events"}


def _alembic_config() -> Config:
    config = Config(str(BACKEND_DIR / "alembic.ini"))
    config.set_main_option("script_location", str(BACKEND_DIR / "migrations"))
    return config


@pytest.fixture
def empty_database_url(engine: Engine, database_url: str) -> Iterator[str]:
    """A brand-new, unmigrated database in the shared container; DATABASE_URL points at it."""
    name = f"migration_{uuid4().hex}"
    with engine.connect().execution_options(isolation_level="AUTOCOMMIT") as connection:
        connection.execute(text(f'CREATE DATABASE "{name}"'))
    url = make_url(database_url).set(database=name).render_as_string(hide_password=False)
    os.environ["DATABASE_URL"] = url
    get_settings.cache_clear()
    try:
        yield url
    finally:
        os.environ["DATABASE_URL"] = database_url
        get_settings.cache_clear()
        with engine.connect().execution_options(isolation_level="AUTOCOMMIT") as connection:
            connection.execute(text(f'DROP DATABASE "{name}" WITH (FORCE)'))


def test_baseline_upgrades_an_empty_database_and_downgrades_cleanly(
    empty_database_url: str,
) -> None:
    config = _alembic_config()
    probe = create_engine(empty_database_url)
    try:
        command.upgrade(config, "head")
        assert set(inspect(probe).get_table_names()) >= DOMAIN_TABLES

        with probe.connect() as connection:
            drift = compare_metadata(MigrationContext.configure(connection), Base.metadata)
        assert drift == [], "models and the baseline migration disagree"

        command.downgrade(config, "base")
        assert DOMAIN_TABLES.isdisjoint(inspect(probe).get_table_names())
    finally:
        probe.dispose()
