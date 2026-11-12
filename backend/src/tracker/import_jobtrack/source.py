"""Read-only access to a JobTrack SQLite database.

Only the in-scope tables are read: organizations, applications and application_events.
JobTrack stores enums as their lowercase values, booleans as 0/1 and datetimes as naive
UTC text, so rows are converted here into plain Python values ready for the new models.
"""

from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from contextlib import closing
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

from tracker.domain import (
    ApplicationEventType,
    ApplicationStatus,
    OrganizationType,
    WorkArrangement,
)

ORGANIZATION_COLUMNS = (
    "id",
    "organization_type",
    "name",
    "normalized_name",
    "industry",
    "location",
    "priority",
    "website_url",
    "career_url",
    "contact_url",
    "notes",
    "created_at",
    "updated_at",
    "archived_at",
)
APPLICATION_COLUMNS = (
    "id",
    "organization_id",
    "role",
    "location",
    "work_arrangement",
    "vacancy_source",
    "vacancy_url",
    "vacancy_age",
    "applied_at",
    "current_status",
    "next_action_at",
    "status_overridden",
    "notes",
    "created_at",
    "updated_at",
    "archived_at",
)
EVENT_COLUMNS = (
    "id",
    "application_id",
    "event_type",
    "occurred_at",
    "notes",
    "resulting_status",
    "created_at",
)


def _datetime(value: str | None) -> datetime | None:
    if value is None:
        return None
    parsed = datetime.fromisoformat(value)
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)


def _date(value: str | None) -> date | None:
    return None if value is None else date.fromisoformat(value)


class JobTrackDatabase:
    """A JobTrack SQLite file, opened read-only."""

    def __init__(self, path: Path) -> None:
        if not path.is_file():
            raise FileNotFoundError(f"JobTrack database not found: {path}")
        self.path = path

    def _rows(self, table: str, columns: tuple[str, ...]) -> list[dict[str, Any]]:
        uri = f"{self.path.resolve().as_uri()}?mode=ro"
        with closing(sqlite3.connect(uri, uri=True)) as connection:
            connection.row_factory = sqlite3.Row
            cursor = connection.execute(f"SELECT {', '.join(columns)} FROM {table} ORDER BY id")
            return [dict(row) for row in cursor]

    def organizations(self) -> Iterator[dict[str, Any]]:
        for row in self._rows("organizations", ORGANIZATION_COLUMNS):
            row["organization_type"] = OrganizationType(row["organization_type"])
            _convert_timestamps(row)
            yield row

    def applications(self) -> Iterator[dict[str, Any]]:
        for row in self._rows("applications", APPLICATION_COLUMNS):
            row["work_arrangement"] = WorkArrangement(row["work_arrangement"])
            row["current_status"] = ApplicationStatus(row["current_status"])
            row["status_overridden"] = bool(row["status_overridden"])
            row["applied_at"] = _date(row["applied_at"])
            row["next_action_at"] = _date(row["next_action_at"])
            row["application_notes"] = row.pop("notes")
            _convert_timestamps(row)
            yield row

    def events(self) -> Iterator[dict[str, Any]]:
        """Application Events in JobTrack id order (status recompute relies on it)."""
        for row in self._rows("application_events", EVENT_COLUMNS):
            row["event_type"] = ApplicationEventType(row["event_type"])
            status = row["resulting_status"]
            row["resulting_status"] = None if status is None else ApplicationStatus(status)
            row["occurred_at"] = _datetime(row["occurred_at"])
            row["created_at"] = _datetime(row["created_at"])
            yield row


def _convert_timestamps(row: dict[str, Any]) -> None:
    for column in ("created_at", "updated_at", "archived_at"):
        row[column] = _datetime(row[column])
