"""Applications: CRUD, filters, status counts, due soon, archive/restore."""

from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from tracker.api.schemas.applications import (
    ApplicationCreate,
    ApplicationDetail,
    ApplicationRead,
    ApplicationUpdate,
    StatusCount,
)
from tracker.db import get_session
from tracker.domain import Application, ApplicationStatus
from tracker.services import ApplicationService, ApplicationSort, SortOrder

router = APIRouter(prefix="/applications", tags=["applications"])

SessionDep = Annotated[Session, Depends(get_session)]


@router.get("", response_model=list[ApplicationRead])
def list_applications(
    session: SessionDep,
    organization: Annotated[
        str | None, Query(description="Case-insensitive substring of the Organization name")
    ] = None,
    role: Annotated[str | None, Query(description="Case-insensitive substring of the role")] = None,
    status: Annotated[
        list[ApplicationStatus] | None,
        Query(description="Keep Applications in any of these Pipeline Statuses"),
    ] = None,
    include_archived: bool = False,
    sort: ApplicationSort = ApplicationSort.APPLIED_AT,
    order: Annotated[
        SortOrder, Query(description="Applications without the sort date come last either way")
    ] = SortOrder.DESC,
) -> list[Application]:
    return ApplicationService(session).search(
        organization_name=organization,
        role=role,
        statuses=status or (),
        include_archived=include_archived,
        sort=sort,
        order=order,
    )


@router.get("/status-counts", response_model=list[StatusCount])
def status_counts(session: SessionDep) -> list[StatusCount]:
    """A count for every Pipeline Status (in pipeline order) over non-archived Applications."""
    counts = ApplicationService(session).status_counts()
    return [StatusCount(status=status, count=count) for status, count in counts.items()]


def get_today() -> date:
    """Today's date; a dependency so tests can pin it."""
    return date.today()


@router.get("/due", response_model=list[ApplicationRead])
def due_applications(
    session: SessionDep,
    server_today: Annotated[date, Depends(get_today)],
    today: Annotated[
        date | None,
        Query(description="The caller's local date (default: the server's date)"),
    ] = None,
) -> list[Application]:
    """Non-archived Applications whose next action date is overdue or within the next
    7 days of ``today``, soonest first."""
    return ApplicationService(session).due(today or server_today)


@router.post("", response_model=ApplicationDetail, status_code=201)
def create_application(payload: ApplicationCreate, session: SessionDep) -> Application:
    application = ApplicationService(session).create(**payload.model_dump())
    session.commit()
    return application


@router.get("/{application_id}", response_model=ApplicationDetail)
def get_application(application_id: int, session: SessionDep) -> Application:
    return ApplicationService(session).get(application_id)


@router.patch("/{application_id}", response_model=ApplicationDetail)
def update_application(
    application_id: int, payload: ApplicationUpdate, session: SessionDep
) -> Application:
    application = ApplicationService(session).update(
        application_id, **payload.model_dump(exclude_unset=True)
    )
    session.commit()
    return application


@router.post("/{application_id}/archive", response_model=ApplicationRead)
def archive_application(application_id: int, session: SessionDep) -> Application:
    application = ApplicationService(session).archive(application_id)
    session.commit()
    return application


@router.post("/{application_id}/restore", response_model=ApplicationRead)
def restore_application(application_id: int, session: SessionDep) -> Application:
    application = ApplicationService(session).restore(application_id)
    session.commit()
    return application
