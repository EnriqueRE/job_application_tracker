"""Request and response models for Organizations."""

from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, field_validator

from tracker.domain import OrganizationType

OrganizationName = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=255)
]
Priority = Annotated[int, Field(ge=0, le=5, description="0 (lowest) to 5 (highest)")]
Industry = Annotated[str, StringConstraints(max_length=128)]
Location = Annotated[str, StringConstraints(max_length=255)]


class OrganizationCreate(BaseModel):
    name: OrganizationName
    organization_type: OrganizationType
    industry: Industry | None = None
    location: Location | None = None
    priority: Priority = 3
    website_url: str | None = None
    career_url: str | None = None
    contact_url: str | None = None
    notes: str | None = None


class OrganizationUpdate(BaseModel):
    """Partial update: only the fields sent change. Name, type and priority can't be null."""

    name: OrganizationName | None = None
    organization_type: OrganizationType | None = None
    industry: Industry | None = None
    location: Location | None = None
    priority: Priority | None = None
    website_url: str | None = None
    career_url: str | None = None
    contact_url: str | None = None
    notes: str | None = None

    @field_validator("name", "organization_type", "priority")
    @classmethod
    def _not_null(cls, value: object) -> object:
        if value is None:
            raise ValueError("may not be null")
        return value


class OrganizationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    organization_type: OrganizationType
    industry: str | None
    location: str | None
    priority: int
    website_url: str | None
    career_url: str | None
    contact_url: str | None
    notes: str | None
    archived_at: datetime | None
    created_at: datetime
    updated_at: datetime
