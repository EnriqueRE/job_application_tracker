"""Shared test harness: real Postgres via testcontainers.

Fixtures for later tickets to reuse:

- ``database_url`` (session): URL of a throwaway Postgres container, already
  migrated to Alembic ``head``. Also exported as ``DATABASE_URL``.
- ``engine`` (session): SQLAlchemy engine bound to that database.
- ``db_session`` (function): a ``Session`` inside a transaction that is rolled
  back after the test. Code may call ``commit()`` freely; commits become
  savepoints and nothing leaks between tests.
- ``client`` (function): a FastAPI ``TestClient`` whose requests use
  ``db_session``, so the test and the app see the same uncommitted data.
"""

import os
from collections.abc import Iterator
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session
from testcontainers.community.postgres import PostgresContainer

from tracker.app import create_app
from tracker.db import get_session
from tracker.settings import get_settings

BACKEND_DIR = Path(__file__).resolve().parent.parent
POSTGRES_IMAGE = "postgres:17-alpine"


def run_migrations(database_url: str) -> None:
    config = Config(str(BACKEND_DIR / "alembic.ini"))
    config.set_main_option("script_location", str(BACKEND_DIR / "migrations"))
    os.environ["DATABASE_URL"] = database_url
    get_settings.cache_clear()
    command.upgrade(config, "head")


@pytest.fixture(scope="session")
def database_url() -> Iterator[str]:
    with PostgresContainer(POSTGRES_IMAGE, driver="psycopg") as postgres:
        url: str = postgres.get_connection_url()
        run_migrations(url)
        yield url
    get_settings.cache_clear()


@pytest.fixture(scope="session")
def engine(database_url: str) -> Iterator[Engine]:
    engine = create_engine(database_url)
    yield engine
    engine.dispose()


@pytest.fixture
def db_session(engine: Engine) -> Iterator[Session]:
    with engine.connect() as connection:
        transaction = connection.begin()
        session = Session(bind=connection, join_transaction_mode="create_savepoint")
        try:
            yield session
        finally:
            session.close()
            transaction.rollback()


@pytest.fixture
def client(db_session: Session) -> Iterator[TestClient]:
    app = create_app()
    app.dependency_overrides[get_session] = lambda: db_session
    with TestClient(app) as test_client:
        yield test_client
