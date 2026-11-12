"""Organization use cases: CRUD, search and archive/restore."""

from typing import Any

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from tracker.domain import Application, Organization, OrganizationType
from tracker.domain.models import utc_now
from tracker.services.errors import (
    DuplicateOrganizationError,
    InvalidValueError,
    NotFoundError,
    OrganizationInUseError,
)

MIN_PRIORITY = 0
MAX_PRIORITY = 5

UPDATABLE_FIELDS = frozenset(
    {
        "name",
        "organization_type",
        "industry",
        "location",
        "priority",
        "website_url",
        "career_url",
        "contact_url",
        "notes",
    }
)


def normalize_name(value: str) -> str:
    """Casefold and collapse whitespace, for matching and uniqueness."""
    return " ".join(value.casefold().split())


def _reject_unknown(fields: dict[str, Any]) -> None:
    unknown = fields.keys() - UPDATABLE_FIELDS
    if unknown:
        raise InvalidValueError(f"Organization has no settable fields {sorted(unknown)}")


class OrganizationService:
    """Operations on Organizations. Methods flush; the caller owns the transaction."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def create(
        self, *, name: str, organization_type: OrganizationType, **fields: Any
    ) -> Organization:
        """Create an Organization; ``fields`` are optional ``UPDATABLE_FIELDS``."""
        _reject_unknown(fields)
        organization = Organization(
            name=name,
            normalized_name=normalize_name(name),
            organization_type=organization_type,
            **fields,
        )
        self._validate(organization)
        self.session.add(organization)
        self.session.flush()
        return organization

    def get(self, organization_id: int) -> Organization:
        organization = self.session.get(Organization, organization_id)
        if organization is None:
            raise NotFoundError(f"Organization {organization_id} was not found")
        return organization

    def search(
        self,
        query: str = "",
        *,
        organization_type: OrganizationType | None = None,
        include_archived: bool = False,
    ) -> list[Organization]:
        """Match ``query`` against name, industry and location; ordered by normalized name."""
        statement = select(Organization)
        if query.strip():
            pattern = f"%{query.strip()}%"
            statement = statement.where(
                or_(
                    Organization.name.ilike(pattern),
                    Organization.industry.ilike(pattern),
                    Organization.location.ilike(pattern),
                )
            )
        if organization_type is not None:
            statement = statement.where(Organization.organization_type == organization_type)
        if not include_archived:
            statement = statement.where(Organization.archived_at.is_(None))
        statement = statement.order_by(Organization.normalized_name, Organization.id)
        return list(self.session.scalars(statement))

    def update(self, organization_id: int, **changes: Any) -> Organization:
        """Change any of ``UPDATABLE_FIELDS``; renaming re-derives the normalized name."""
        _reject_unknown(changes)
        organization = self.get(organization_id)
        with self.session.no_autoflush:
            for field, value in changes.items():
                setattr(organization, field, value)
            organization.normalized_name = normalize_name(organization.name)
            self._validate(organization)
        self.session.flush()
        return organization

    def archive(self, organization_id: int) -> Organization:
        organization = self.get(organization_id)
        organization.archived_at = utc_now()
        self.session.flush()
        return organization

    def restore(self, organization_id: int) -> Organization:
        organization = self.get(organization_id)
        organization.archived_at = None
        self.session.flush()
        return organization

    def delete(self, organization_id: int) -> None:
        """Delete an Organization that has no Applications (archived ones included)."""
        organization = self.get(organization_id)
        has_applications = self.session.scalar(
            select(Application.id).where(Application.organization_id == organization_id).limit(1)
        )
        if has_applications is not None:
            raise OrganizationInUseError(
                f"Organization {organization_id} still has Applications; archive it instead"
            )
        self.session.delete(organization)
        self.session.flush()

    def _validate(self, organization: Organization) -> None:
        priority = organization.priority
        if priority is not None and not MIN_PRIORITY <= priority <= MAX_PRIORITY:
            raise InvalidValueError(
                f"priority must be between {MIN_PRIORITY} and {MAX_PRIORITY}, got {priority}"
            )
        clash = self.session.scalar(
            select(Organization.id).where(
                Organization.organization_type == organization.organization_type,
                Organization.normalized_name == organization.normalized_name,
                Organization.id != organization.id if organization.id is not None else True,
            )
        )
        if clash is not None:
            raise DuplicateOrganizationError(
                f"A {organization.organization_type} named {organization.name!r} already exists"
            )
