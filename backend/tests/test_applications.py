"""ApplicationService: Application CRUD, search, archive/restore and delete."""

from datetime import date

import pytest
from sqlalchemy.orm import Session

from tracker.domain import (
    ApplicationEventType,
    ApplicationStatus,
    Organization,
    OrganizationType,
    WorkArrangement,
)
from tracker.services import (
    ApplicationService,
    InvalidValueError,
    NotFoundError,
    OrganizationInUseError,
    OrganizationService,
)


@pytest.fixture
def organizations(db_session: Session) -> OrganizationService:
    return OrganizationService(db_session)


@pytest.fixture
def applications(db_session: Session) -> ApplicationService:
    return ApplicationService(db_session)


@pytest.fixture
def acme(organizations: OrganizationService) -> Organization:
    return organizations.create(name="Acme", organization_type=OrganizationType.COMPANY)


def test_new_application_starts_saved_with_its_markdown_texts(
    applications: ApplicationService, acme: Organization
) -> None:
    created = applications.create(
        organization_id=acme.id,
        role="Backend Engineer",
        job_description="# Backend Engineer\n\nPython, Postgres.",
        interview_notes="- Ask about on-call",
        application_notes="Referred by Ana",
    )

    fetched = applications.get(created.id)
    assert fetched.organization == acme
    assert fetched.current_status is ApplicationStatus.SAVED
    assert fetched.status_overridden is False
    assert fetched.work_arrangement is WorkArrangement.UNSPECIFIED
    assert fetched.job_description == "# Backend Engineer\n\nPython, Postgres."
    assert fetched.interview_notes == "- Ask about on-call"
    assert fetched.application_notes == "Referred by Ana"
    assert fetched.archived_at is None


def test_application_needs_an_existing_organization(applications: ApplicationService) -> None:
    with pytest.raises(NotFoundError):
        applications.create(organization_id=999_999, role="Engineer")


def test_getting_a_missing_application_raises_not_found(
    applications: ApplicationService,
) -> None:
    with pytest.raises(NotFoundError):
        applications.get(999_999)


def test_search_filters_and_orders_by_most_recently_applied(
    applications: ApplicationService, organizations: OrganizationService, acme: Organization
) -> None:
    globex = organizations.create(name="Globex", organization_type=OrganizationType.COMPANY)
    older = applications.create(
        organization_id=acme.id,
        role="Data Engineer",
        applied_at=date(2026, 1, 5),
        vacancy_source="LinkedIn",
        location="Remote, MX",
    )
    newer = applications.create(
        organization_id=globex.id,
        role="Platform Engineer",
        applied_at=date(2026, 3, 1),
        application_notes="salary 90k",
    )
    unapplied = applications.create(organization_id=acme.id, role="SRE")

    assert applications.search() == [newer, older, unapplied]
    assert applications.search("data") == [older]
    assert applications.search("SALARY") == [newer]
    assert applications.search("globex") == [newer]
    assert applications.search(organization_id=acme.id) == [older, unapplied]
    assert applications.search(source="linked") == [older]
    assert applications.search(location="mx") == [older]
    assert applications.search(status=ApplicationStatus.SAVED) == [newer, older, unapplied]
    assert applications.search(status=ApplicationStatus.APPLIED) == []


def test_update_changes_fields_but_not_the_pipeline_status(
    applications: ApplicationService, acme: Organization
) -> None:
    application = applications.create(organization_id=acme.id, role="Engineer")

    updated = applications.update(
        application.id,
        role="Senior Engineer",
        work_arrangement=WorkArrangement.REMOTE,
        interview_notes="Talk about migrations",
    )

    assert updated.role == "Senior Engineer"
    assert updated.work_arrangement is WorkArrangement.REMOTE
    assert updated.interview_notes == "Talk about migrations"
    with pytest.raises(InvalidValueError):
        applications.update(application.id, current_status=ApplicationStatus.OFFER)


def test_moving_an_application_to_a_missing_organization_is_rejected(
    applications: ApplicationService, acme: Organization
) -> None:
    application = applications.create(organization_id=acme.id, role="Engineer")

    with pytest.raises(NotFoundError):
        applications.update(application.id, organization_id=999_999)


def test_archived_applications_are_hidden_until_restored(
    applications: ApplicationService, acme: Organization
) -> None:
    kept = applications.create(organization_id=acme.id, role="Engineer")
    archived = applications.create(organization_id=acme.id, role="Manager")

    applications.archive(archived.id)

    assert archived.archived_at is not None
    assert applications.search() == [kept]
    assert set(applications.search(include_archived=True)) == {kept, archived}

    applications.restore(archived.id)

    assert archived.archived_at is None
    assert set(applications.search()) == {kept, archived}


def test_deleting_an_application_removes_its_events(
    applications: ApplicationService, acme: Organization
) -> None:
    application = applications.create(organization_id=acme.id, role="Engineer")
    event = applications.add_event(application.id, ApplicationEventType.APPLIED)

    applications.delete(application.id)

    with pytest.raises(NotFoundError):
        applications.get(application.id)
    with pytest.raises(NotFoundError):
        applications.get_event(event.id)


def test_an_organization_with_applications_cannot_be_deleted(
    applications: ApplicationService, organizations: OrganizationService, acme: Organization
) -> None:
    application = applications.create(organization_id=acme.id, role="Engineer")

    with pytest.raises(OrganizationInUseError):
        organizations.delete(acme.id)

    applications.delete(application.id)
    organizations.delete(acme.id)

    with pytest.raises(NotFoundError):
        organizations.get(acme.id)
