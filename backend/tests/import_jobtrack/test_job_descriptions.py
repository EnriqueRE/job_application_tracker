"""Strict matching of JobTrack Markdown files to Applications, and what the report says."""

from sqlalchemy.orm import Session

from import_jobtrack.source import JobTrackSource
from tracker.domain import Application
from tracker.import_jobtrack import (
    ImportReport,
    MatchedFile,
    UnmatchedFile,
    import_jobtrack,
)
from tracker.services import ApplicationService


def _import(session: Session, source: JobTrackSource) -> ImportReport:
    return import_jobtrack(
        session, sqlite_path=source.sqlite_path, markdown_dir=source.markdown_dir
    )


def _by_role(session: Session) -> dict[str, Application]:
    return {a.role: a for a in ApplicationService(session).search(include_archived=True)}


def test_a_matching_file_stores_only_the_body_as_the_job_description(
    db_session: Session, source: JobTrackSource
) -> None:
    org = source.organization("Autozone")
    app = source.application(org, "Lead Developer-Commercial")
    source.job_description_file(
        "rejected/7-autozone-lead-developer-commercial.md",
        application_id=app,
        heading="Lead Developer-Commercial — Autozone",
        body="This position supports sales.\r\n\r\n    Indented paste\r\n- Perks: café",
    )

    report = _import(db_session, source)

    application = _by_role(db_session)["Lead Developer-Commercial"]
    assert application.job_description == (
        "This position supports sales.\n\n    Indented paste\n- Perks: café"
    )
    assert report.matched_files == [
        MatchedFile(
            path="rejected/7-autozone-lead-developer-commercial.md",
            jobtrack_application_id=app,
            application_id=application.id,
            has_job_description=True,
        )
    ]
    assert report.unmatched_files == []
    assert report.applications_without_job_description == []


def test_files_sharing_an_application_id_attach_only_where_the_heading_matches(
    db_session: Session, source: JobTrackSource
) -> None:
    safran = source.organization("Safran")
    app = source.application(safran, "Software Technical Referent")
    source.job_description_file(
        "applied/37-safran-software-technical-referent.md",
        application_id=app,
        heading="Software Technical Referent — Safran",
        body="Safran body",
    )
    source.job_description_file(
        "applied/37-autozone-lead-developer-commercial.md",
        application_id=app,
        heading="Lead Developer-Commercial — Autozone",
        body="Autozone body",
    )

    report = _import(db_session, source)

    assert _by_role(db_session)["Software Technical Referent"].job_description == "Safran body"
    assert [m.path for m in report.matched_files] == [
        "applied/37-safran-software-technical-referent.md"
    ]
    assert report.unmatched_files == [
        UnmatchedFile(
            path="applied/37-autozone-lead-developer-commercial.md",
            reason="heading_mismatch",
            detail=(
                f"Application {app} is 'Software Technical Referent — Safran', "
                "file heading is 'Lead Developer-Commercial — Autozone'"
            ),
        )
    ]


def test_a_reversed_heading_is_not_guessed(db_session: Session, source: JobTrackSource) -> None:
    org = source.organization("Concentrix")
    app = source.application(org, "Technical Solutions Consultant")
    source.job_description_file(
        "rejected/13-concentrix.md",
        application_id=app,
        heading="Concentrix — Technical Solutions Consultant",
        body="Body",
    )

    report = _import(db_session, source)

    assert _by_role(db_session)["Technical Solutions Consultant"].job_description is None
    assert [(u.path, u.reason) for u in report.unmatched_files] == [
        ("rejected/13-concentrix.md", "heading_mismatch")
    ]


def test_an_empty_body_means_no_job_description(
    db_session: Session, source: JobTrackSource
) -> None:
    org = source.organization("Asiamart")
    app = source.application(org, "-")
    source.job_description_file(
        "applied/22-asiamart.md", application_id=app, heading="- — Asiamart", body="  \r\n"
    )

    report = _import(db_session, source)

    application = _by_role(db_session)["-"]
    assert application.job_description is None
    assert report.matched_files == [
        MatchedFile(
            path="applied/22-asiamart.md",
            jobtrack_application_id=app,
            application_id=application.id,
            has_job_description=False,
        )
    ]
    [missing] = report.applications_without_job_description
    assert (missing.jobtrack_application_id, missing.application_id) == (app, application.id)
    assert (missing.role, missing.organization) == ("-", "Asiamart")


def test_two_files_matching_the_same_application_are_ambiguous(
    db_session: Session, source: JobTrackSource
) -> None:
    org = source.organization("Acme")
    app = source.application(org, "Engineer")
    for name in ("applied/1-acme-engineer.md", "rejected/1-acme-engineer.md"):
        source.job_description_file(
            name, application_id=app, heading="Engineer — Acme", body=f"Body of {name}"
        )

    report = _import(db_session, source)

    assert _by_role(db_session)["Engineer"].job_description is None
    assert report.matched_files == []
    assert sorted((u.path, u.reason) for u in report.unmatched_files) == [
        ("applied/1-acme-engineer.md", "ambiguous"),
        ("rejected/1-acme-engineer.md", "ambiguous"),
    ]
    assert len(report.applications_without_job_description) == 1


def test_unknown_ids_and_unparseable_files_are_reported_and_aggregates_ignored(
    db_session: Session, source: JobTrackSource
) -> None:
    org = source.organization("Acme")
    app = source.application(org, "Engineer")
    source.job_description_file(
        "applied/99-ghost.md", application_id=99, heading="Ghost — Nowhere", body="Body"
    )
    source.job_description_file(
        "applied/x-no-id.md", application_id=None, heading="Engineer — Acme", body="Body"
    )
    source.write_file(
        "applied/x-no-section.md", f"# Engineer — Acme\r\n\r\n- Application ID: {app}\r\n"
    )
    aggregate = (
        f"<!-- Source: applied/1.md -->\r\n# Engineer — Acme\r\n\r\n- Application ID: {app}\r\n"
        "\r\n## Job description\r\n\r\nAggregated\r\n---\r\n"
    )
    source.write_file("no_response.md", aggregate)
    source.write_file("rejections.md", aggregate)
    source.write_file("applied/.gitkeep", "")

    report = _import(db_session, source)

    assert _by_role(db_session)["Engineer"].job_description is None
    assert report.matched_files == []
    assert sorted((u.path, u.reason) for u in report.unmatched_files) == [
        ("applied/99-ghost.md", "no_application_with_id"),
        ("applied/x-no-id.md", "unparseable"),
        ("applied/x-no-section.md", "unparseable"),
    ]
