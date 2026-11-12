"""Load a JobTrack database and its Markdown Job Descriptions into the new schema."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from tracker.db import Base
from tracker.domain import Application, ApplicationEvent, Organization
from tracker.import_jobtrack import job_descriptions
from tracker.import_jobtrack.job_descriptions import UnmatchedFile
from tracker.import_jobtrack.mapping import ImportedEntity, JobTrackImportMapping
from tracker.import_jobtrack.source import JobTrackDatabase


@dataclass
class EntityCounts:
    source: int = 0
    """Rows found in JobTrack."""
    created: int = 0
    already_imported: int = 0
    """Skipped because an earlier run imported them."""
    reused_existing: int = 0
    """Matched to a row that already existed (Organizations with the same type and name)."""


@dataclass(frozen=True)
class MatchedFile:
    path: str
    jobtrack_application_id: int
    application_id: int
    has_job_description: bool
    """False when the file's body is empty."""


@dataclass(frozen=True)
class ApplicationWithoutJobDescription:
    jobtrack_application_id: int
    application_id: int
    role: str
    organization: str


@dataclass
class ImportReport:
    counts: dict[str, EntityCounts] = field(
        default_factory=lambda: {
            "organizations": EntityCounts(),
            "applications": EntityCounts(),
            "application_events": EntityCounts(),
        }
    )
    matched_files: list[MatchedFile] = field(default_factory=list)
    unmatched_files: list[UnmatchedFile] = field(default_factory=list)
    applications_without_job_description: list[ApplicationWithoutJobDescription] = field(
        default_factory=list
    )

    def to_json(self) -> dict[str, Any]:
        return asdict(self)


class _Mappings:
    """The persisted JobTrack-id -> new-id mapping for one entity."""

    def __init__(self, session: Session, entity: ImportedEntity) -> None:
        self.session = session
        self.entity = entity
        rows = session.scalars(
            select(JobTrackImportMapping).where(JobTrackImportMapping.entity == entity.value)
        )
        self.ids = {row.jobtrack_id: row.new_id for row in rows}

    def record(self, jobtrack_id: int, new_id: int) -> None:
        self.session.add(
            JobTrackImportMapping(entity=self.entity.value, jobtrack_id=jobtrack_id, new_id=new_id)
        )
        self.ids[jobtrack_id] = new_id

    def resolve(self, jobtrack_id: int, referrer: int) -> int:
        """The new id for a referenced JobTrack row; fails the import if it does not exist."""
        try:
            return self.ids[jobtrack_id]
        except KeyError:
            raise ValueError(
                f"JobTrack row {referrer} refers to missing {self.entity.value} {jobtrack_id}"
            ) from None


def import_jobtrack(session: Session, *, sqlite_path: Path, markdown_dir: Path) -> ImportReport:
    """Import into ``session``. Only flushes: the caller commits or rolls back.

    JobTrack rows imported by an earlier run (per ``jobtrack_import_map``) are skipped, so
    re-running creates no duplicates and leaves rows edited since the first run alone.
    """
    database = JobTrackDatabase(sqlite_path)
    source_organizations = list(database.organizations())
    source_applications = list(database.applications())
    source_events = list(database.events())
    report = ImportReport()

    organization_names = {row["id"]: row["name"] for row in source_organizations}
    headings = {
        row["id"]: (row["role"], organization_names[row["organization_id"]])
        for row in source_applications
    }
    matched = job_descriptions.match(markdown_dir, headings)
    report.unmatched_files = sorted(matched.unmatched, key=lambda u: u.path)

    organizations = _import_organizations(session, source_organizations, report)

    applications = _Mappings(session, ImportedEntity.APPLICATION)
    counts = report.counts["applications"]
    for row in source_applications:
        counts.source += 1
        jobtrack_id = row.pop("id")
        file = matched.matches.get(jobtrack_id)
        if jobtrack_id in applications.ids:
            counts.already_imported += 1
        else:
            counts.created += 1
            row["organization_id"] = organizations.resolve(row["organization_id"], jobtrack_id)
            row["job_description"] = file.body if file else None
            applications.record(jobtrack_id, _insert(session, Application, row))
        application_id = applications.ids[jobtrack_id]
        if file is not None:
            report.matched_files.append(
                MatchedFile(file.path, jobtrack_id, application_id, file.body is not None)
            )
        if file is None or file.body is None:
            role, organization = headings[jobtrack_id]
            report.applications_without_job_description.append(
                ApplicationWithoutJobDescription(jobtrack_id, application_id, role, organization)
            )
    report.matched_files.sort(key=lambda m: m.path)

    events = _Mappings(session, ImportedEntity.APPLICATION_EVENT)
    counts = report.counts["application_events"]
    for row in source_events:
        counts.source += 1
        jobtrack_id = row.pop("id")
        if jobtrack_id in events.ids:
            counts.already_imported += 1
            continue
        counts.created += 1
        row["application_id"] = applications.resolve(row["application_id"], jobtrack_id)
        events.record(jobtrack_id, _insert(session, ApplicationEvent, row))

    session.flush()
    return report


def _import_organizations(
    session: Session, rows: list[dict[str, Any]], report: ImportReport
) -> _Mappings:
    organizations = _Mappings(session, ImportedEntity.ORGANIZATION)
    counts = report.counts["organizations"]
    for row in rows:
        counts.source += 1
        jobtrack_id = row.pop("id")
        if jobtrack_id in organizations.ids:
            counts.already_imported += 1
            continue
        existing = session.scalar(
            select(Organization).where(
                Organization.organization_type == row["organization_type"],
                Organization.normalized_name == row["normalized_name"],
            )
        )
        if existing is not None:
            counts.reused_existing += 1
            organizations.record(jobtrack_id, existing.id)
            continue
        counts.created += 1
        organizations.record(jobtrack_id, _insert(session, Organization, row))
    return organizations


def _insert(session: Session, model: type[Base], values: dict[str, Any]) -> int:
    instance = model(**values)
    session.add(instance)
    session.flush()
    new_id: int = instance.id  # type: ignore[attr-defined]
    return new_id
