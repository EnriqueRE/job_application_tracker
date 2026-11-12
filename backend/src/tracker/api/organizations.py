"""Organizations: list/search, create, read, update, archive and restore."""

from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from tracker.api.schemas.organizations import (
    OrganizationCreate,
    OrganizationRead,
    OrganizationUpdate,
)
from tracker.db import get_session
from tracker.domain import Organization, OrganizationType
from tracker.services import OrganizationService

router = APIRouter(prefix="/organizations", tags=["organizations"])

SessionDep = Annotated[Session, Depends(get_session)]

_NOT_FOUND: dict[int | str, dict[str, Any]] = {404: {"description": "Organization not found"}}


@router.get("", response_model=list[OrganizationRead])
def list_organizations(
    session: SessionDep,
    q: Annotated[str, Query(description="Matches name, industry or location")] = "",
    organization_type: OrganizationType | None = None,
    include_archived: bool = False,
) -> list[Organization]:
    """Organizations ordered by name; archived ones only with ``include_archived``."""
    return OrganizationService(session).search(
        q, organization_type=organization_type, include_archived=include_archived
    )


@router.post(
    "",
    response_model=OrganizationRead,
    status_code=status.HTTP_201_CREATED,
    responses={409: {"description": "An Organization of that type and name already exists"}},
)
def create_organization(body: OrganizationCreate, session: SessionDep) -> Organization:
    organization = OrganizationService(session).create(**body.model_dump())
    session.commit()
    return organization


@router.get("/{organization_id}", response_model=OrganizationRead, responses=_NOT_FOUND)
def get_organization(organization_id: int, session: SessionDep) -> Organization:
    return OrganizationService(session).get(organization_id)


@router.patch(
    "/{organization_id}",
    response_model=OrganizationRead,
    responses={**_NOT_FOUND, 409: {"description": "Another Organization has that type and name"}},
)
def update_organization(
    organization_id: int, body: OrganizationUpdate, session: SessionDep
) -> Organization:
    """Change only the fields sent."""
    organization = OrganizationService(session).update(
        organization_id, **body.model_dump(exclude_unset=True)
    )
    session.commit()
    return organization


@router.post(
    "/{organization_id}/archive",
    response_model=OrganizationRead,
    responses={**_NOT_FOUND, 409: {"description": "The Organization has active Applications"}},
)
def archive_organization(organization_id: int, session: SessionDep) -> Organization:
    """Archive an Organization. Blocked (409) while it has active Applications."""
    organization = OrganizationService(session).archive(organization_id)
    session.commit()
    return organization


@router.post("/{organization_id}/restore", response_model=OrganizationRead, responses=_NOT_FOUND)
def restore_organization(organization_id: int, session: SessionDep) -> Organization:
    organization = OrganizationService(session).restore(organization_id)
    session.commit()
    return organization
