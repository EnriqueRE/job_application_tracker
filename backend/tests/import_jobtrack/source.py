"""Builders for small, synthetic JobTrack inputs (SQLite database + Markdown files).

The SQLite tables mirror JobTrack's stored schema (alembic head ``0002_job_description_path``),
including the provenance columns the importer must ignore. CHECK constraints are left out so
tests can plant invalid values.
"""

from __future__ import annotations

import sqlite3
from contextlib import closing
from itertools import count
from pathlib import Path
from typing import Any

SCHEMA = """
CREATE TABLE organizations (
    id INTEGER PRIMARY KEY, organization_type VARCHAR(15) NOT NULL, name VARCHAR(255) NOT NULL,
    normalized_name VARCHAR(255) NOT NULL, industry VARCHAR(128), location VARCHAR(255),
    priority INTEGER NOT NULL, website_url TEXT, career_url TEXT, contact_url TEXT, notes TEXT,
    created_at DATETIME NOT NULL, updated_at DATETIME NOT NULL, archived_at DATETIME,
    source_sheet VARCHAR(128), source_row INTEGER, raw_source_text TEXT, import_run_id INTEGER
);
CREATE TABLE applications (
    id INTEGER PRIMARY KEY, organization_id INTEGER NOT NULL, role VARCHAR(255) NOT NULL,
    location VARCHAR(255), work_arrangement VARCHAR(11) NOT NULL, vacancy_source VARCHAR(255),
    vacancy_url TEXT, vacancy_age VARCHAR(128), applied_at DATE,
    current_status VARCHAR(19) NOT NULL,
    next_action_at DATE, status_overridden BOOLEAN NOT NULL, notes TEXT, source_key VARCHAR(255),
    created_at DATETIME NOT NULL, updated_at DATETIME NOT NULL, archived_at DATETIME,
    source_sheet VARCHAR(128), source_row INTEGER, raw_source_text TEXT, import_run_id INTEGER,
    job_description_path TEXT
);
CREATE TABLE application_events (
    id INTEGER PRIMARY KEY, application_id INTEGER NOT NULL, event_type VARCHAR(19) NOT NULL,
    occurred_at DATETIME, notes TEXT, resulting_status VARCHAR(19), created_at DATETIME NOT NULL,
    source_sheet VARCHAR(128), source_row INTEGER, raw_source_text TEXT, import_run_id INTEGER
);
CREATE TABLE contacts (id INTEGER PRIMARY KEY, name TEXT);
CREATE TABLE tasks (id INTEGER PRIMARY KEY, title TEXT);
"""

STAMP = "2026-07-30 23:15:01.612109"


class JobTrackSource:
    """A JobTrack SQLite database plus a ``job_applications/`` Markdown directory."""

    def __init__(self, root: Path) -> None:
        self.sqlite_path = root / "jobtrack.db"
        self.markdown_dir = root / "job_applications"
        self.markdown_dir.mkdir()
        self._ids = count(1)
        with closing(sqlite3.connect(self.sqlite_path)) as connection:
            connection.executescript(SCHEMA)

    def raw(self, sql: str, params: tuple[Any, ...] = ()) -> None:
        with closing(sqlite3.connect(self.sqlite_path)) as connection, connection:
            connection.execute(sql, params)

    def _insert(self, table: str, row: dict[str, Any]) -> int:
        columns = ", ".join(row)
        marks = ", ".join("?" for _ in row)
        self.raw(f"INSERT INTO {table} ({columns}) VALUES ({marks})", tuple(row.values()))
        return int(row["id"])

    def organization(self, name: str = "Acme", **fields: Any) -> int:
        row: dict[str, Any] = {
            "id": next(self._ids),
            "organization_type": "company",
            "name": name,
            "normalized_name": " ".join(name.casefold().split()),
            "priority": 3,
            "created_at": STAMP,
            "updated_at": STAMP,
            "source_sheet": "Companies",
            "source_row": 7,
            "raw_source_text": "raw",
        }
        row.update(fields)
        return self._insert("organizations", row)

    def application(self, organization_id: int, role: str = "Engineer", **fields: Any) -> int:
        row: dict[str, Any] = {
            "id": next(self._ids),
            "organization_id": organization_id,
            "role": role,
            "work_arrangement": "unspecified",
            "current_status": "saved",
            "status_overridden": 0,
            "created_at": STAMP,
            "updated_at": STAMP,
            "source_key": f"key-{role}",
            "job_description_path": "job_applications/saved/stale.md",
        }
        row.update(fields)
        return self._insert("applications", row)

    def event(self, application_id: int, event_type: str = "applied", **fields: Any) -> int:
        row: dict[str, Any] = {
            "id": next(self._ids),
            "application_id": application_id,
            "event_type": event_type,
            "created_at": STAMP,
        }
        row.update(fields)
        return self._insert("application_events", row)

    def job_description_file(
        self,
        relative_path: str,
        *,
        application_id: int | None,
        heading: str,
        body: str = "",
        status: str = "applied",
    ) -> Path:
        """Write a file in JobTrack's template, with CRLF line endings like the real ones."""
        lines = [f"# {heading}", ""]
        if application_id is not None:
            lines.append(f"- Application ID: {application_id}")
        lines += [f"- Status: {status}", "- Vacancy URL: ", "- Captured: 2026-08-03", ""]
        lines += ["## Job description", "", body]
        return self.write_file(relative_path, "\r\n".join(lines) + "\r\n")

    def write_file(self, relative_path: str, content: str) -> Path:
        path = self.markdown_dir / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content.encode("utf-8"))
        return path
