import os
from collections.abc import Iterator
from pathlib import Path
from uuid import uuid4

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import Engine, text
from sqlalchemy.engine import make_url

from import_jobtrack.source import JobTrackSource
from tracker.settings import get_settings

BACKEND_DIR = Path(__file__).resolve().parents[2]


@pytest.fixture
def source(tmp_path: Path) -> JobTrackSource:
    return JobTrackSource(tmp_path)


@pytest.fixture
def fresh_database_url(engine: Engine, database_url: str) -> Iterator[str]:
    """A new, migrated database the CLI can commit to (the shared one is per-test rolled back)."""
    name = f"import_{uuid4().hex}"
    with engine.connect().execution_options(isolation_level="AUTOCOMMIT") as connection:
        connection.execute(text(f'CREATE DATABASE "{name}"'))
    url = make_url(database_url).set(database=name).render_as_string(hide_password=False)
    config = Config(str(BACKEND_DIR / "alembic.ini"))
    config.set_main_option("script_location", str(BACKEND_DIR / "migrations"))
    os.environ["DATABASE_URL"] = url
    get_settings.cache_clear()
    try:
        command.upgrade(config, "head")
        yield url
    finally:
        os.environ["DATABASE_URL"] = database_url
        get_settings.cache_clear()
        with engine.connect().execution_options(isolation_level="AUTOCOMMIT") as connection:
            connection.execute(text(f'DROP DATABASE "{name}" WITH (FORCE)'))
