"""Request and response models for the Applications API."""

from datetime import date, datetime
from typing import Annotated, Self
from urllib.parse import urlsplit

from pydantic import AfterValidator, BaseModel, ConfigDict, Field, model_validator

from tracker.domain import (
    ApplicationEventType,
    ApplicationStatus,
    OrganizationType,
    WorkArrangement,
)


def _http_url(value: str) -> str:
    parts = urlsplit(value)
    if parts.scheme not in ("http", "https") or not parts.netloc or " " in value:
        raise ValueError("must be a URL starting with http:// or https://")
    return value


HttpUrlString = Annotated[str, Field(max_length=2048), AfterValidator(_http_url)]
"""An http(s) URL kept exactly as entered (no normalization)."""


class ApplicationOrganization(BaseModel):
    """The Organization an Application belongs to, as embedded in Application responses."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    organization_type: OrganizationType


class ApplicationTimelineEvent(BaseModel):
    """One Application Event in an Application's timeline."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    event_type: ApplicationEventType
    occurred_at: datetime | None
    notes: str | None
    resulting_status: ApplicationStatus | None
    created_at: datetime


class ApplicationCreate(BaseModel):
    organization_id: int
    role: str = Field(min_length=1, max_length=255)
    location: str | None = Field(default=None, max_length=255)
    work_arrangement: WorkArrangement = WorkArrangement.UNSPECIFIED
    vacancy_source: str | None = Field(default=None, max_length=255)
    vacancy_url: HttpUrlString | None = None
    vacancy_age: str | None = Field(default=None, max_length=128)
    applied_at: date | None = None
    next_action_at: date | None = None
    job_description: str | None = None
    interview_notes: str | None = None
    application_notes: str | None = None


class ApplicationUpdate(BaseModel):
    """Partial update: only the fields sent change. The Pipeline Status is not settable here;
    it changes through Application Events or the Status Override."""

    model_config = ConfigDict(extra="forbid")

    organization_id: int | None = None
    role: str | None = Field(default=None, min_length=1, max_length=255)
    location: str | None = Field(default=None, max_length=255)
    work_arrangement: WorkArrangement | None = None
    vacancy_source: str | None = Field(default=None, max_length=255)
    vacancy_url: HttpUrlString | None = None
    vacancy_age: str | None = Field(default=None, max_length=128)
    applied_at: date | None = None
    next_action_at: date | None = None
    job_description: str | None = None
    interview_notes: str | None = None
    application_notes: str | None = None

    @model_validator(mode="after")
    def _required_fields_are_not_cleared(self) -> Self:
        for field in ("organization_id", "role", "work_arrangement"):
            if field in self.model_fields_set and getattr(self, field) is None:
                raise ValueError(f"{field} cannot be null")
        return self


class ApplicationRead(BaseModel):
    """An Application as shown in lists (without its Markdown texts or timeline)."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    organization: ApplicationOrganization
    role: str
    location: str | None
    work_arrangement: WorkArrangement
    vacancy_source: str | None
    vacancy_url: str | None
    vacancy_age: str | None
    applied_at: date | None
    next_action_at: date | None
    current_status: ApplicationStatus
    """The Pipeline Status."""
    status_overridden: bool
    """True while a Status Override is in effect."""
    created_at: datetime
    updated_at: datetime
    archived_at: datetime | None


class StatusCount(BaseModel):
    """How many non-archived Applications are in one Pipeline Status."""

    status: ApplicationStatus
    count: int


class ApplicationDetail(ApplicationRead):
    """An Application with its Job Description, Interview Notes, Application Notes and
    Application Event timeline (oldest first)."""

    job_description: str | None
    interview_notes: str | None
    application_notes: str | None
    events: list[ApplicationTimelineEvent]
