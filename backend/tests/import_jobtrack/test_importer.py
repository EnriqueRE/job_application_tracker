"""Importing a JobTrack database and its Markdown Job Descriptions into Postgres."""

from datetime import UTC, date, datetime

from sqlalchemy.orm import Session

from import_jobtrack.source import JobTrackSource
from tracker.domain import (
    ApplicationEventType,
    ApplicationStatus,
    OrganizationType,
    WorkArrangement,
)
from tracker.import_jobtrack import EntityCounts, ImportReport, import_jobtrack
from tracker.services import ApplicationService, OrganizationService


def _import(session: Session, source: JobTrackSource) -> ImportReport:
    return import_jobtrack(
        session, sqlite_path=source.sqlite_path, markdown_dir=source.markdown_dir
    )


def test_organizations_are_imported_with_their_fields_and_timestamps(
    db_session: Session, source: JobTrackSource
) -> None:
    source.organization(
        "Hays Recruiting",
        organization_type="recruiting_firm",
        industry="Staffing",
        location="Monterrey",
        priority=5,
        website_url="https://hays.example",
        notes="Talked to them in July",
        created_at="2026-07-01 10:00:00.000000",
        updated_at="2026-07-02 11:30:00.500000",
        archived_at="2026-08-01 09:00:00.000000",
    )

    _import(db_session, source)

    [organization] = OrganizationService(db_session).search(include_archived=True)
    assert organization.name == "Hays Recruiting"
    assert organization.normalized_name == "hays recruiting"
    assert organization.organization_type is OrganizationType.RECRUITING_FIRM
    assert organization.industry == "Staffing"
    assert organization.location == "Monterrey"
    assert organization.priority == 5
    assert organization.website_url == "https://hays.example"
    assert organization.notes == "Talked to them in July"
    assert organization.created_at == datetime(2026, 7, 1, 10, tzinfo=UTC)
    assert organization.updated_at == datetime(2026, 7, 2, 11, 30, 0, 500000, tzinfo=UTC)
    assert organization.archived_at == datetime(2026, 8, 1, 9, tzinfo=UTC)


def test_applications_keep_pipeline_status_override_and_notes_as_stored(
    db_session: Session, source: JobTrackSource
) -> None:
    org = source.organization("Safran")
    source.application(
        org,
        "Software Technical Referent",
        location="Querétaro",
        work_arrangement="hybrid",
        vacancy_source="LinkedIn",
        vacancy_url="https://jobs.example/1",
        vacancy_age="2 weeks",
        applied_at="2026-06-15",
        next_action_at="2026-07-01",
        current_status="rejected",
        status_overridden=1,
        notes="Referred by a friend",
        archived_at="2026-09-01 08:00:00.000000",
    )

    _import(db_session, source)

    [application] = ApplicationService(db_session).search(include_archived=True)
    assert application.organization.name == "Safran"
    assert application.role == "Software Technical Referent"
    assert application.location == "Querétaro"
    assert application.work_arrangement is WorkArrangement.HYBRID
    assert application.vacancy_source == "LinkedIn"
    assert application.vacancy_url == "https://jobs.example/1"
    assert application.vacancy_age == "2 weeks"
    assert application.applied_at == date(2026, 6, 15)
    assert application.next_action_at == date(2026, 7, 1)
    assert application.current_status is ApplicationStatus.REJECTED
    assert application.status_overridden is True
    assert application.application_notes == "Referred by a friend"
    assert application.interview_notes is None
    assert application.archived_at == datetime(2026, 9, 1, 8, tzinfo=UTC)


def test_rerunning_the_import_creates_no_duplicates(
    db_session: Session, source: JobTrackSource
) -> None:
    org = source.organization()
    app = source.application(org)
    source.event(app, "applied", resulting_status="applied")

    first = _import(db_session, source)
    second = _import(db_session, source)

    assert first.counts == {
        "organizations": EntityCounts(source=1, created=1, already_imported=0),
        "applications": EntityCounts(source=1, created=1, already_imported=0),
        "application_events": EntityCounts(source=1, created=1, already_imported=0),
    }
    assert second.counts == {
        "organizations": EntityCounts(source=1, created=0, already_imported=1),
        "applications": EntityCounts(source=1, created=0, already_imported=1),
        "application_events": EntityCounts(source=1, created=0, already_imported=1),
    }
    assert len(OrganizationService(db_session).search()) == 1
    [application] = ApplicationService(db_session).search()
    assert len(ApplicationService(db_session).list_events(application.id)) == 1


def test_rerun_imports_only_rows_added_to_jobtrack_since_the_last_run(
    db_session: Session, source: JobTrackSource
) -> None:
    org = source.organization("Acme")
    source.application(org, "Engineer")
    _import(db_session, source)

    source.application(org, "Architect")
    report = _import(db_session, source)

    assert report.counts["applications"] == EntityCounts(source=2, created=1, already_imported=1)
    roles = sorted(a.role for a in ApplicationService(db_session).search())
    assert roles == ["Architect", "Engineer"]
    assert {a.organization.name for a in ApplicationService(db_session).search()} == {"Acme"}


def test_an_existing_organization_with_the_same_name_is_reused_not_duplicated(
    db_session: Session, source: JobTrackSource
) -> None:
    existing = OrganizationService(db_session).create(
        name="ACME", organization_type=OrganizationType.COMPANY
    )
    org = source.organization("Acme")
    source.application(org)

    report = _import(db_session, source)

    assert report.counts["organizations"] == EntityCounts(
        source=1, created=0, already_imported=0, reused_existing=1
    )
    [application] = ApplicationService(db_session).search()
    assert application.organization_id == existing.id


def test_application_events_are_copied_in_order_without_recomputing_status(
    db_session: Session, source: JobTrackSource
) -> None:
    org = source.organization()
    app = source.application(org, current_status="applied")
    source.event(
        app,
        "applied",
        occurred_at="2026-06-15 00:00:00.000000",
        resulting_status="applied",
        notes="Via portal",
    )
    source.event(app, "note", notes="Undated note")
    # Copied as stored: the rejection does not move the stored Pipeline Status.
    source.event(app, "rejected", resulting_status="rejected", created_at="2026-07-01 12:00:00")

    _import(db_session, source)

    [application] = ApplicationService(db_session).search()
    assert application.current_status is ApplicationStatus.APPLIED
    events = ApplicationService(db_session).list_events(application.id)
    stamp = datetime(2026, 7, 30, 23, 15, 1, 612109, tzinfo=UTC)
    assert [
        (e.event_type, e.occurred_at, e.notes, e.resulting_status, e.created_at) for e in events
    ] == [
        (
            ApplicationEventType.APPLIED,
            datetime(2026, 6, 15, tzinfo=UTC),
            "Via portal",
            ApplicationStatus.APPLIED,
            stamp,
        ),
        (ApplicationEventType.NOTE, None, "Undated note", None, stamp),
        (
            ApplicationEventType.REJECTED,
            None,
            None,
            ApplicationStatus.REJECTED,
            datetime(2026, 7, 1, 12, tzinfo=UTC),
        ),
    ]
