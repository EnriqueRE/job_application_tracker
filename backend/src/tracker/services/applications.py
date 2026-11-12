"""Application use cases: CRUD, search, archive/restore, Application Events and the
Pipeline Status they derive, and the Status Override."""

from collections.abc import Collection
from datetime import date, datetime, timedelta
from enum import StrEnum
from typing import Any

from sqlalchemy import func, select
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

EVENT_UPDATABLE_FIELDS = frozenset({"event_type", "occurred_at", "notes", "resulting_status"})


DUE_SOON_DAYS = 7
"""An Application is due soon when its next action date is overdue or within this many days."""


class ApplicationSort(StrEnum):
    """Date columns an Application list can be sorted by."""

    APPLIED_AT = "applied_at"
    NEXT_ACTION_AT = "next_action_at"
    UPDATED_AT = "updated_at"


class SortOrder(StrEnum):
    ASC = "asc"
    DESC = "desc"


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
        *,
        organization_name: str | None = None,
        role: str | None = None,
        statuses: Collection[ApplicationStatus] = (),
        include_archived: bool = False,
        sort: ApplicationSort = ApplicationSort.APPLIED_AT,
        order: SortOrder = SortOrder.DESC,
    ) -> list[Application]:
        """Filter Applications. ``organization_name`` and ``role`` are case-insensitive
        substrings; ``statuses`` keeps Applications in any of the given Pipeline Statuses.

        Ordered by the ``sort`` date in ``order`` (Applications without that date last either
        way), then newest id. Default: most recently applied first.
        """
        statement = select(Application).join(Application.organization)
        if organization_name and organization_name.strip():
            statement = statement.where(Organization.name.ilike(f"%{organization_name.strip()}%"))
        if role and role.strip():
            statement = statement.where(Application.role.ilike(f"%{role.strip()}%"))
        if statuses:
            statement = statement.where(Application.current_status.in_(statuses))
        if not include_archived:
            statement = statement.where(Application.archived_at.is_(None))
        column = getattr(Application, sort.value)
        direction = column.asc() if order is SortOrder.ASC else column.desc()
        statement = statement.order_by(direction.nulls_last(), Application.id.desc())
        return list(self.session.scalars(statement))

    def status_counts(self) -> dict[ApplicationStatus, int]:
        """How many non-archived Applications are in each Pipeline Status (every status
        present, in pipeline order, zero when empty)."""
        rows = self.session.execute(
            select(Application.current_status, func.count())
            .where(Application.archived_at.is_(None))
            .group_by(Application.current_status)
        )
        counts: dict[ApplicationStatus, int] = dict.fromkeys(ApplicationStatus, 0)
        for status, count in rows:
            counts[status] = count
        return counts

    def due(self, today: date, *, within_days: int = DUE_SOON_DAYS) -> list[Application]:
        """Non-archived Applications whose next action date is overdue or at most
        ``within_days`` after ``today``, soonest first (then oldest id)."""
        statement = (
            select(Application)
            .where(
                Application.archived_at.is_(None),
                Application.next_action_at.is_not(None),
                Application.next_action_at <= today + timedelta(days=within_days),
            )
            .order_by(Application.next_action_at.asc(), Application.id.asc())
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
        """Append an Application Event; a status-bearing one sets the Pipeline Status
        (unless a Status Override is in effect), any other leaves it unchanged.

        ``resulting_status`` defaults to the status the event type implies (if any).
        """
        application = self.get(application_id)
        status = resulting_status or status_for_event(event_type)
        event = ApplicationEvent(
            application=application,
            event_type=event_type,
            occurred_at=occurred_at,
            notes=notes,
            resulting_status=status,
        )
        self.session.add(event)
        if status is not None and not application.status_overridden:
            application.current_status = status
        self.session.flush()
        return event

    def list_events(self, application_id: int) -> list[ApplicationEvent]:
        """An Application's timeline, in the order the events were added."""
        return list(self.get(application_id).events)

    def update_event(self, event_id: int, **changes: Any) -> ApplicationEvent:
        """Change any of ``EVENT_UPDATABLE_FIELDS`` and re-derive the Pipeline Status.

        Changing ``event_type`` without a ``resulting_status`` re-derives the event's
        resulting status from the new type.
        """
        unknown = changes.keys() - EVENT_UPDATABLE_FIELDS
        if unknown:
            raise InvalidValueError(f"Application Event has no settable fields {sorted(unknown)}")
        event = self.get_event(event_id)
        if "event_type" in changes and changes.get("resulting_status") is None:
            changes["resulting_status"] = status_for_event(changes["event_type"])
        for field, value in changes.items():
            setattr(event, field, value)
        self.session.flush()
        self._derive_status(event.application)
        return event

    def delete_event(self, event_id: int) -> None:
        """Remove an Application Event and re-derive the Pipeline Status."""
        event = self.get_event(event_id)
        application = event.application
        application.events.remove(event)
        self.session.flush()
        self._derive_status(application)

    # Status Override

    def set_status_override(self, application_id: int, status: ApplicationStatus) -> Application:
        """Pin the Pipeline Status by hand; Application Events stop changing it."""
        application = self.get(application_id)
        application.current_status = status
        application.status_overridden = True
        self.session.flush()
        return application

    def clear_status_override(self, application_id: int) -> Application:
        """Resume event-derived Pipeline Status and recompute it now."""
        application = self.get(application_id)
        application.status_overridden = False
        self._derive_status(application)
        return application

    def _derive_status(self, application: Application) -> None:
        """Set the Pipeline Status from the latest-added status-bearing Application Event
        (``saved`` if there is none), unless a Status Override is in effect."""
        if application.status_overridden:
            return
        latest = self.session.scalar(
            select(ApplicationEvent.resulting_status)
            .where(
                ApplicationEvent.application_id == application.id,
                ApplicationEvent.resulting_status.is_not(None),
            )
            .order_by(ApplicationEvent.id.desc())
            .limit(1)
        )
        application.current_status = latest or ApplicationStatus.SAVED
        self.session.flush()

    def _require_organization(self, organization_id: int) -> None:
        if self.session.get(Organization, organization_id) is None:
            raise NotFoundError(f"Organization {organization_id} was not found")
