"""A real backup/restore round trip, following the root README.

``backup/backup.sh`` runs inside a Postgres container (as the Compose ``backup`` service
does, as the host user), then the dump is restored into a fresh, empty Postgres with the
README's ``pg_restore`` command, and the data and Alembic revision must survive.
"""

import os
import shlex
from collections.abc import Iterator
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session
from testcontainers.community.postgres import PostgresContainer

from tracker.domain import ApplicationEventType, ApplicationStatus, OrganizationType
from tracker.services import ApplicationService, OrganizationService
from tracker.settings import get_settings

# The image the Compose ``db`` and ``backup`` services use.
COMPOSE_POSTGRES_IMAGE = "postgres:17.7-alpine"
BACKEND_DIR = Path(__file__).resolve().parent.parent
BACKUP_SCRIPTS = BACKEND_DIR.parent / "backup"


def _alembic_config() -> Config:
    config = Config(str(BACKEND_DIR / "alembic.ini"))
    config.set_main_option("script_location", str(BACKEND_DIR / "migrations"))
    return config


def _upgrade_to_head(database_url: str, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DATABASE_URL", database_url)
    get_settings.cache_clear()
    try:
        command.upgrade(_alembic_config(), "head")
    finally:
        get_settings.cache_clear()


@pytest.fixture
def backups(tmp_path: Path) -> Path:
    path = tmp_path / "backups"
    path.mkdir()
    return path


def _postgres(backups: Path) -> PostgresContainer:
    return (
        PostgresContainer(COMPOSE_POSTGRES_IMAGE, driver="psycopg")
        .with_volume_mapping(str(BACKUP_SCRIPTS), "/backup", "ro")
        .with_volume_mapping(str(backups), "/backups", "rw")
    )


def _exec(container: PostgresContainer, script: str, **kwargs: object) -> str:
    result = container.get_wrapped_container().exec_run(["sh", "-c", script], **kwargs)
    output: str = result.output.decode()
    assert result.exit_code == 0, output
    return output


@pytest.fixture
def source(backups: Path) -> Iterator[PostgresContainer]:
    with _postgres(backups) as postgres:
        yield postgres


@pytest.fixture
def target(backups: Path) -> Iterator[PostgresContainer]:
    with _postgres(backups) as postgres:
        yield postgres


def _seed(database_url: str) -> None:
    engine = create_engine(database_url)
    with Session(engine) as session, session.begin():
        acme = OrganizationService(session).create(
            name="Acme", organization_type=OrganizationType.COMPANY
        )
        applications = ApplicationService(session)
        application = applications.create(
            organization_id=acme.id, role="Engineer", job_description="# Ñandú role"
        )
        applications.add_event(application.id, ApplicationEventType.SCREENING, notes="Call")
    engine.dispose()


def test_a_backup_restores_into_a_fresh_database(
    source: PostgresContainer,
    target: PostgresContainer,
    backups: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source_url = source.get_connection_url()
    _upgrade_to_head(source_url, monkeypatch)
    _seed(source_url)

    _exec(
        source,
        "/backup/backup.sh",
        user=f"{os.getuid()}:{os.getgid()}",
        environment={
            "PGHOST": "localhost",
            "PGUSER": source.username,
            "PGPASSWORD": source.password,
            "PGDATABASE": source.dbname,
            "BACKUP_DIR": "/backups",
        },
    )
    [dump] = [p.name for p in backups.iterdir()]
    assert dump.startswith("tracker-")

    # The README's restore command, run in the fresh `db` container.
    _exec(
        target,
        'pg_restore -U "$POSTGRES_USER" -d "$POSTGRES_DB" --no-owner --exit-on-error '
        f"--single-transaction < /backups/{shlex.quote(dump)}",
    )

    target_url = target.get_connection_url()
    engine = create_engine(target_url)
    with Session(engine) as session:
        [application] = ApplicationService(session).search()
        assert application.organization.name == "Acme"
        assert application.role == "Engineer"
        assert application.job_description == "# Ñandú role"
        assert application.current_status is ApplicationStatus.SCREENING
        assert [e.notes for e in application.events] == ["Call"]
        revision = session.scalar(text("SELECT version_num FROM alembic_version"))
    engine.dispose()

    # `app` runs `alembic upgrade head` on start; after a restore it has nothing to do.
    assert revision == ScriptDirectory.from_config(_alembic_config()).get_current_head()
    _upgrade_to_head(target_url, monkeypatch)
