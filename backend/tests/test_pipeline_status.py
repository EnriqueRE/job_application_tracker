"""Application Events derive the Pipeline Status, unless a Status Override is in effect."""

from datetime import UTC, datetime

import pytest
from sqlalchemy.orm import Session

from tracker.domain import (
    EVENT_STATUS,
    Application,
    ApplicationEventType,
    ApplicationStatus,
    OrganizationType,
)
from tracker.services import (
    ApplicationService,
    InvalidValueError,
    NotFoundError,
    OrganizationService,
)

Event = ApplicationEventType
Status = ApplicationStatus


@pytest.fixture
def applications(db_session: Session) -> ApplicationService:
    return ApplicationService(db_session)


@pytest.fixture
def application(db_session: Session, applications: ApplicationService) -> Application:
    acme = OrganizationService(db_session).create(
        name="Acme", organization_type=OrganizationType.COMPANY
    )
    return applications.create(organization_id=acme.id, role="Engineer")


def test_events_derive_status_and_respect_a_status_override(
    applications: ApplicationService, application: Application
) -> None:
    applied = applications.add_event(application.id, Event.APPLIED)
    assert applied.resulting_status is Status.APPLIED
    assert applications.get(application.id).current_status is Status.APPLIED

    applications.set_status_override(application.id, Status.REJECTED)
    assert applications.get(application.id).current_status is Status.REJECTED
    assert applications.get(application.id).status_overridden is True

    screening = applications.add_event(application.id, Event.SCREENING)
    assert screening.resulting_status is Status.SCREENING
    assert applications.get(application.id).current_status is Status.REJECTED

    applications.clear_status_override(application.id)
    assert applications.get(application.id).status_overridden is False
    assert applications.get(application.id).current_status is Status.SCREENING


def test_note_event_does_not_change_status(
    applications: ApplicationService, application: Application
) -> None:
    applications.add_event(application.id, Event.APPLIED)

    note = applications.add_event(application.id, Event.NOTE, notes="Recruiter called")

    assert note.resulting_status is None
    assert note.notes == "Recruiter called"
    assert applications.get(application.id).current_status is Status.APPLIED


def test_every_status_is_reachable_from_some_event(
    applications: ApplicationService, application: Application
) -> None:
    reached = set()
    for event_type in EVENT_STATUS:
        applications.add_event(application.id, event_type)
        reached.add(applications.get(application.id).current_status)

    assert reached == set(ApplicationStatus)


def test_interview_events_map_to_interview(
    applications: ApplicationService, application: Application
) -> None:
    applications.add_event(application.id, Event.INTERVIEW_SCHEDULED)
    assert applications.get(application.id).current_status is Status.INTERVIEW

    applications.add_event(application.id, Event.TECHNICAL_INTERVIEW)
    applications.add_event(application.id, Event.INTERVIEW_COMPLETED)
    assert applications.get(application.id).current_status is Status.INTERVIEW


def test_an_explicit_resulting_status_wins_over_the_event_type(
    applications: ApplicationService, application: Application
) -> None:
    event = applications.add_event(
        application.id, Event.FOLLOW_UP, resulting_status=Status.NO_RESPONSE
    )

    assert event.resulting_status is Status.NO_RESPONSE
    assert applications.get(application.id).current_status is Status.NO_RESPONSE


def test_clearing_an_override_without_status_bearing_events_returns_to_saved(
    applications: ApplicationService, application: Application
) -> None:
    applications.add_event(application.id, Event.NOTE)
    applications.set_status_override(application.id, Status.OFFER)

    applications.clear_status_override(application.id)

    assert applications.get(application.id).current_status is Status.SAVED


def test_the_latest_added_event_decides_even_if_it_occurred_earlier(
    applications: ApplicationService, application: Application
) -> None:
    applications.add_event(
        application.id, Event.SCREENING, occurred_at=datetime(2026, 3, 1, tzinfo=UTC)
    )
    applications.add_event(
        application.id, Event.APPLIED, occurred_at=datetime(2026, 2, 1, tzinfo=UTC)
    )

    assert applications.get(application.id).current_status is Status.APPLIED


def test_events_are_listed_in_the_order_they_were_added(
    applications: ApplicationService, application: Application
) -> None:
    first = applications.add_event(application.id, Event.APPLIED)
    second = applications.add_event(application.id, Event.NOTE)

    assert applications.list_events(application.id) == [first, second]


def test_adding_an_event_to_a_missing_application_raises_not_found(
    applications: ApplicationService,
) -> None:
    with pytest.raises(NotFoundError):
        applications.add_event(999_999, Event.APPLIED)


def test_editing_the_latest_events_type_recomputes_the_status(
    applications: ApplicationService, application: Application
) -> None:
    applications.add_event(application.id, Event.APPLIED)
    event = applications.add_event(application.id, Event.SCREENING)

    edited = applications.update_event(event.id, event_type=Event.REJECTED)

    assert edited.resulting_status is Status.REJECTED
    assert applications.get(application.id).current_status is Status.REJECTED


def test_editing_an_event_into_a_note_falls_back_to_the_previous_status(
    applications: ApplicationService, application: Application
) -> None:
    applications.add_event(application.id, Event.APPLIED)
    event = applications.add_event(application.id, Event.SCREENING)

    edited = applications.update_event(event.id, event_type=Event.NOTE, notes="Just a call")

    assert edited.resulting_status is None
    assert edited.notes == "Just a call"
    assert applications.get(application.id).current_status is Status.APPLIED


def test_editing_only_the_date_or_notes_keeps_the_resulting_status(
    applications: ApplicationService, application: Application
) -> None:
    event = applications.add_event(
        application.id, Event.FOLLOW_UP, resulting_status=Status.NO_RESPONSE
    )
    when = datetime(2026, 4, 2, 9, 30, tzinfo=UTC)

    edited = applications.update_event(event.id, occurred_at=when, notes="Pinged again")

    assert edited.occurred_at == when
    assert edited.resulting_status is Status.NO_RESPONSE
    assert applications.get(application.id).current_status is Status.NO_RESPONSE


def test_editing_unknown_event_fields_is_rejected(
    applications: ApplicationService, application: Application
) -> None:
    event = applications.add_event(application.id, Event.APPLIED)

    with pytest.raises(InvalidValueError):
        applications.update_event(event.id, application_id=application.id + 1)


def test_deleting_the_latest_event_falls_back_to_the_previous_status(
    applications: ApplicationService, application: Application
) -> None:
    applied = applications.add_event(application.id, Event.APPLIED)
    rejected = applications.add_event(application.id, Event.REJECTED)

    applications.delete_event(rejected.id)
    assert applications.get(application.id).current_status is Status.APPLIED
    assert applications.list_events(application.id) == [applied]

    applications.delete_event(applied.id)
    assert applications.get(application.id).current_status is Status.SAVED

    with pytest.raises(NotFoundError):
        applications.get_event(applied.id)


def test_event_edits_and_deletes_leave_an_overridden_status_alone(
    applications: ApplicationService, application: Application
) -> None:
    applications.add_event(application.id, Event.APPLIED)
    screening = applications.add_event(application.id, Event.SCREENING)
    applications.set_status_override(application.id, Status.OFFER)

    applications.update_event(screening.id, event_type=Event.REJECTED)
    assert applications.get(application.id).current_status is Status.OFFER

    applications.delete_event(screening.id)
    assert applications.get(application.id).current_status is Status.OFFER

    applications.clear_status_override(application.id)
    assert applications.get(application.id).current_status is Status.APPLIED
