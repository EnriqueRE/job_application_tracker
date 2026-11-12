"""Schemas for an Application's timeline (Application Events) and its Status Override."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, field_validator

from tracker.domain import ApplicationEventType, ApplicationStatus


class ApplicationStatusRead(BaseModel):
    """An Application's Pipeline Status after a timeline or Status Override change."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    current_status: ApplicationStatus
    status_overridden: bool


class ApplicationEventRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    application_id: int
    event_type: ApplicationEventType
    occurred_at: datetime | None
    notes: str | None
    resulting_status: ApplicationStatus | None
    created_at: datetime


class ApplicationEventCreate(BaseModel):
    """A new Application Event. ``resulting_status`` defaults to the status the
    event type implies (none for ``contacted``, ``follow_up`` and ``note``)."""

    event_type: ApplicationEventType
    occurred_at: datetime | None = None
    notes: str | None = None
    resulting_status: ApplicationStatus | None = None


class ApplicationEventUpdate(BaseModel):
    """Fields to change on an Application Event; omitted fields stay as they are.

    Changing ``event_type`` without a ``resulting_status`` re-derives the resulting
    status from the new type.
    """

    event_type: ApplicationEventType | None = None
    occurred_at: datetime | None = None
    notes: str | None = None
    resulting_status: ApplicationStatus | None = None

    @field_validator("event_type")
    @classmethod
    def _event_type_not_null(cls, value: ApplicationEventType | None) -> ApplicationEventType:
        if value is None:
            raise ValueError("event_type cannot be null; omit it to keep the current type")
        return value


class StatusOverrideSet(BaseModel):
    """The Pipeline Status to pin by hand."""

    status: ApplicationStatus


class ApplicationEventMutation(BaseModel):
    """The event that was added or edited, plus the Application's updated Pipeline Status."""

    event: ApplicationEventRead
    application: ApplicationStatusRead
