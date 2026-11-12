"""Application use cases: CRUD, search, archive/restore, Application Events and the
Pipeline Status they derive, and the Status Override."""

from datetime import datetime
from typing import Any

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from tracker.domain import (
    Application,
    ApplicationEvent,
    ApplicationEventType,
    ApplicationStatus,
    Organization,
    status_for_event,
)
from tracker.domain.models import utc_now
from tracker.services.errors import InvalidValueError, NotFoundError

UPDATABLE_FIELDS = frozenset(
    {
        "organization_id",
        "role",
        "location",
        "work_arrangement",
        "vacancy_source",
        "vacancy_url",
        "vacancy_age",
        "applied_at",
        "next_action_at",
        "job_description",
        "interview_notes",
        "application_notes",
    }
)
"""Fields ``create``/``update`` accept. The Pipeline Status is not among them: it changes only
through Application Events or the Status Override."""


def _reject_unknown(fields: dict[str, Any]) -> None:
    unknown = fields.keys() - UPDATABLE_FIELDS
    if unknown:
        raise InvalidValueError(f"Application has no settable fields {sorted(unknown)}")


class ApplicationService:
    """Operations on Applications and their Application Events.

    Methods flush; the caller owns the transaction.
    """

    def __init__(self, session: Session) -> None:
        self.session = session

    # Applications

    def create(self, *, organization_id: int, role: str, **fields: Any) -> Application:
        """Create an Application in ``saved``; ``fields`` are optional ``UPDATABLE_FIELDS``."""
        _reject_unknown(fields)
        self._require_organization(organization_id)
        application = Application(organization_id=organization_id, role=role, **fields)
        self.session.add(application)
        self.session.flush()
        return application

    def get(self, application_id: int) -> Application:
        application = self.session.get(Application, application_id)
        if application is None:
            raise NotFoundError(f"Application {application_id} was not found")
        return application

    def search(
        self,
        query: str = "",
        *,
        status: ApplicationStatus | None = None,
        organization_id: int | None = None,
        source: str | None = None,
        location: str | None = None,
        include_archived: bool = False,
    ) -> list[Application]:
        """Filter Applications. ``query`` matches role, Application Notes or Organization name.

        Ordered by ``applied_at`` (most recent first, unapplied last), then newest id.
        """
        statement = select(Application).join(Application.organization)
        if query.strip():
            pattern = f"%{query.strip()}%"
            statement = statement.where(
                or_(
                    Application.role.ilike(pattern),
                    Application.application_notes.ilike(pattern),
                    Organization.name.ilike(pattern),
                )
            )
        if status is not None:
            statement = statement.where(Application.current_status == status)
        if organization_id is not None:
            statement = statement.where(Application.organization_id == organization_id)
        if source and source.strip():
            statement = statement.where(Application.vacancy_source.ilike(f"%{source.strip()}%"))
        if location and location.strip():
            statement = statement.where(Application.location.ilike(f"%{location.strip()}%"))
        if not include_archived:
            statement = statement.where(Application.archived_at.is_(None))
        statement = statement.order_by(
            Application.applied_at.desc().nulls_last(), Application.id.desc()
        )
        return list(self.session.scalars(statement))

    def update(self, application_id: int, **changes: Any) -> Application:
        """Change any of ``UPDATABLE_FIELDS``."""
        _reject_unknown(changes)
        application = self.get(application_id)
        if "organization_id" in changes:
            self._require_organization(changes["organization_id"])
        for field, value in changes.items():
            setattr(application, field, value)
        self.session.flush()
        return application

    def archive(self, application_id: int) -> Application:
        application = self.get(application_id)
        application.archived_at = utc_now()
        self.session.flush()
        return application

    def restore(self, application_id: int) -> Application:
        application = self.get(application_id)
        application.archived_at = None
        self.session.flush()
        return application

    def delete(self, application_id: int) -> None:
        """Delete an Application and its Application Events for good."""
        self.session.delete(self.get(application_id))
        self.session.flush()

    # Application Events

    def get_event(self, event_id: int) -> ApplicationEvent:
        event = self.session.get(ApplicationEvent, event_id)
        if event is None:
            raise NotFoundError(f"Application Event {event_id} was not found")
        return event

    def add_event(
        self,
        application_id: int,
        event_type: ApplicationEventType,
        *,
        occurred_at: datetime | None = None,
        notes: str | None = None,
        resulting_status: ApplicationStatus | None = None,
    ) -> ApplicationEvent:
        """Append an Application Event and re-derive the Pipeline Status.

        ``resulting_status`` defaults to the status the event type implies (if any).
        """
        application = self.get(application_id)
        event = ApplicationEvent(
            application=application,
            event_type=event_type,
            occurred_at=occurred_at,
            notes=notes,
            resulting_status=resulting_status or status_for_event(event_type),
        )
        self.session.add(event)
        self.session.flush()
        return event

    def _require_organization(self, organization_id: int) -> None:
        if self.session.get(Organization, organization_id) is None:
            raise NotFoundError(f"Organization {organization_id} was not found")
