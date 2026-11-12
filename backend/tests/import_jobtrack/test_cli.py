"""The ``python -m tracker.import_jobtrack`` command: one transaction and a JSON report."""

import json
from collections.abc import Iterator
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from import_jobtrack.source import JobTrackSource
from tracker.import_jobtrack.__main__ import main
from tracker.services import ApplicationService, OrganizationService


@pytest.fixture
def target(fresh_database_url: str) -> Iterator[Session]:
    engine = create_engine(fresh_database_url)
    with Session(engine) as session:
        yield session
    engine.dispose()


def _run(source: JobTrackSource, report: Path, database_url: str) -> None:
    main(
        [
            "--sqlite",
            str(source.sqlite_path),
            "--markdown-dir",
            str(source.markdown_dir),
            "--report",
            str(report),
            "--database-url",
            database_url,
        ]
    )


def test_cli_commits_the_import_and_writes_a_json_report(
    source: JobTrackSource, tmp_path: Path, fresh_database_url: str, target: Session
) -> None:
    org = source.organization("Acme")
    app = source.application(org, "Engineer")
    source.application(org, "Architect")
    source.event(app, "applied", resulting_status="applied")
    source.job_description_file(
        "applied/1-acme-engineer.md", application_id=app, heading="Engineer — Acme", body="Body"
    )
    source.job_description_file(
        "applied/1-other.md", application_id=app, heading="Other — Acme", body="Body"
    )
    report_path = tmp_path / "report.json"

    _run(source, report_path, fresh_database_url)

    assert sorted(a.role for a in ApplicationService(target).search()) == ["Architect", "Engineer"]
    report = json.loads(report_path.read_text())
    assert report["counts"] == {
        "organizations": {"source": 1, "created": 1, "already_imported": 0, "reused_existing": 0},
        "applications": {"source": 2, "created": 2, "already_imported": 0, "reused_existing": 0},
        "application_events": {
            "source": 1,
            "created": 1,
            "already_imported": 0,
            "reused_existing": 0,
        },
    }
    assert [m["path"] for m in report["matched_files"]] == ["applied/1-acme-engineer.md"]
    assert [(u["path"], u["reason"]) for u in report["unmatched_files"]] == [
        ("applied/1-other.md", "heading_mismatch")
    ]
    assert [a["role"] for a in report["applications_without_job_description"]] == ["Architect"]


def test_running_the_cli_twice_creates_no_duplicates(
    source: JobTrackSource, tmp_path: Path, fresh_database_url: str, target: Session
) -> None:
    org = source.organization("Acme")
    source.event(source.application(org), "applied")

    _run(source, tmp_path / "first.json", fresh_database_url)
    _run(source, tmp_path / "second.json", fresh_database_url)

    assert len(OrganizationService(target).search()) == 1
    assert len(ApplicationService(target).search()) == 1
    second = json.loads((tmp_path / "second.json").read_text())
    assert {name: c["created"] for name, c in second["counts"].items()} == {
        "organizations": 0,
        "applications": 0,
        "application_events": 0,
    }


def test_a_failure_part_way_leaves_postgres_unchanged_and_writes_no_report(
    source: JobTrackSource, tmp_path: Path, fresh_database_url: str, target: Session
) -> None:
    org = source.organization("Acme")
    source.application(org)
    source.event(application_id=999, event_type="applied")  # dangling: fails after inserts
    report_path = tmp_path / "report.json"

    with pytest.raises(ValueError, match="refers to missing application 999"):
        _run(source, report_path, fresh_database_url)

    assert OrganizationService(target).search(include_archived=True) == []
    assert ApplicationService(target).search(include_archived=True) == []
    assert not report_path.exists()


def test_a_report_that_cannot_be_written_leaves_postgres_unchanged(
    source: JobTrackSource, tmp_path: Path, fresh_database_url: str, target: Session
) -> None:
    source.application(source.organization("Acme"))
    report_path = tmp_path / "missing-dir" / "report.json"

    with pytest.raises(FileNotFoundError):
        _run(source, report_path, fresh_database_url)

    assert OrganizationService(target).search(include_archived=True) == []
    assert ApplicationService(target).search(include_archived=True) == []
