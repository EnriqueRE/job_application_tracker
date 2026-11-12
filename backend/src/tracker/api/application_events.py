"""Application Events (an Application's timeline) and the Status Override.

Every mutation answers with the Application's updated Pipeline Status, so the UI can
refresh without a second call.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from tracker.api.schemas.application_events import (
    ApplicationEventCreate,
    ApplicationEventMutation,
    ApplicationEventRead,
    ApplicationEventUpdate,
    ApplicationStatusRead,
    StatusOverrideSet,
)
from tracker.db import get_session
from tracker.domain import Application, ApplicationEvent
from tracker.services import ApplicationService, NotFoundError

router = APIRouter(prefix="/applications/{application_id}", tags=["application-events"])

SessionDep = Annotated[Session, Depends(get_session)]


def _event_of(service: ApplicationService, application_id: int, event_id: int) -> ApplicationEvent:
    """The Application Event, if it is on this Application's timeline."""
    event = service.get_event(event_id)
    if event.application_id != service.get(application_id).id:
        raise NotFoundError(
            f"Application Event {event_id} was not found on Application {application_id}"
        )
    return event


def _mutation(event: ApplicationEvent, application: Application) -> ApplicationEventMutation:
    return ApplicationEventMutation(
        event=ApplicationEventRead.model_validate(event),
        application=ApplicationStatusRead.model_validate(application),
    )


@router.post(
    "/events", response_model=ApplicationEventMutation, status_code=status.HTTP_201_CREATED
)
def add_application_event(
    application_id: int, body: ApplicationEventCreate, session: SessionDep
) -> ApplicationEventMutation:
    """Add an Application Event and re-derive the Pipeline Status."""
    service = ApplicationService(session)
    event = service.add_event(application_id, **body.model_dump())
    session.commit()
    return _mutation(event, service.get(application_id))


@router.get("/events", response_model=list[ApplicationEventRead])
def list_application_events(application_id: int, session: SessionDep) -> list[ApplicationEvent]:
    """The Application's timeline, in the order the events were added."""
    return ApplicationService(session).list_events(application_id)


@router.patch("/events/{event_id}", response_model=ApplicationEventMutation)
def update_application_event(
    application_id: int, event_id: int, body: ApplicationEventUpdate, session: SessionDep
) -> ApplicationEventMutation:
    """Edit an Application Event and re-derive the Pipeline Status."""
    service = ApplicationService(session)
    _event_of(service, application_id, event_id)
    event = service.update_event(event_id, **body.model_dump(exclude_unset=True))
    session.commit()
    return _mutation(event, service.get(application_id))


@router.delete("/events/{event_id}", response_model=ApplicationStatusRead)
def delete_application_event(
    application_id: int, event_id: int, session: SessionDep
) -> Application:
    """Remove an Application Event and re-derive the Pipeline Status."""
    service = ApplicationService(session)
    _event_of(service, application_id, event_id)
    service.delete_event(event_id)
    session.commit()
    return service.get(application_id)


@router.put("/status-override", response_model=ApplicationStatusRead)
def set_status_override(
    application_id: int, body: StatusOverrideSet, session: SessionDep
) -> Application:
    """Pin the Pipeline Status by hand; Application Events stop changing it."""
    application = ApplicationService(session).set_status_override(application_id, body.status)
    session.commit()
    return application


@router.delete("/status-override", response_model=ApplicationStatusRead)
def clear_status_override(application_id: int, session: SessionDep) -> Application:
    """Clear the Status Override and re-derive the Pipeline Status from Application Events."""
    application = ApplicationService(session).clear_status_override(application_id)
    session.commit()
    return application
