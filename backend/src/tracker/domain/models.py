"""ORM models for Organization, Application and Application Event."""

from __future__ import annotations

from datetime import UTC, date, datetime
from enum import StrEnum

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from tracker.db import Base
from tracker.domain.enums import (
    ApplicationEventType,
    ApplicationStatus,
    OrganizationType,
    WorkArrangement,
)


def utc_now() -> datetime:
    return datetime.now(UTC)


def _enum_column(enum_class: type[StrEnum], name: str) -> SAEnum:
    """VARCHAR + CHECK constraint holding the lowercase enum values."""
    return SAEnum(
        enum_class,
        values_callable=lambda members: [member.value for member in members],
        native_enum=False,
        create_constraint=True,
        name=name,
    )


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False
    )


class ArchiveMixin:
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Organization(Base, TimestampMixin, ArchiveMixin):
    """A company, recruiter, recruiting firm, or job portal."""

    __tablename__ = "organizations"

    id: Mapped[int] = mapped_column(primary_key=True)
    organization_type: Mapped[OrganizationType] = mapped_column(
        _enum_column(OrganizationType, "organization_type"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    normalized_name: Mapped[str] = mapped_column(String(255), nullable=False)
    industry: Mapped[str | None] = mapped_column(String(128))
    location: Mapped[str | None] = mapped_column(String(255))
    priority: Mapped[int] = mapped_column(Integer, default=3, nullable=False)
    website_url: Mapped[str | None] = mapped_column(Text)
    career_url: Mapped[str | None] = mapped_column(Text)
    contact_url: Mapped[str | None] = mapped_column(Text)
    notes: Mapped[str | None] = mapped_column(Text)

    applications: Mapped[list[Application]] = relationship(back_populates="organization")

    __table_args__ = (
        UniqueConstraint(
            "organization_type", "normalized_name", name="organization_type_normalized_name"
        ),
        CheckConstraint("priority BETWEEN 0 AND 5", name="priority_range"),
        Index("ix_organizations_type_name", "organization_type", "normalized_name"),
        Index("ix_organizations_archived_at", "archived_at"),
    )


class Application(Base, TimestampMixin, ArchiveMixin):
    """One job opportunity being pursued at one Organization."""

    __tablename__ = "applications"

    id: Mapped[int] = mapped_column(primary_key=True)
    organization_id: Mapped[int] = mapped_column(
        ForeignKey("organizations.id", ondelete="RESTRICT"), nullable=False
    )
    role: Mapped[str] = mapped_column(String(255), nullable=False)
    location: Mapped[str | None] = mapped_column(String(255))
    work_arrangement: Mapped[WorkArrangement] = mapped_column(
        _enum_column(WorkArrangement, "work_arrangement"),
        default=WorkArrangement.UNSPECIFIED,
        nullable=False,
    )
    vacancy_source: Mapped[str | None] = mapped_column(String(255))
    vacancy_url: Mapped[str | None] = mapped_column(Text)
    vacancy_age: Mapped[str | None] = mapped_column(String(128))
    applied_at: Mapped[date | None] = mapped_column(Date)
    current_status: Mapped[ApplicationStatus] = mapped_column(
        _enum_column(ApplicationStatus, "application_status"),
        default=ApplicationStatus.SAVED,
        nullable=False,
    )
    """The Pipeline Status."""
    next_action_at: Mapped[date | None] = mapped_column(Date)
    status_overridden: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    """True while a Status Override is in effect."""
    job_description: Mapped[str | None] = mapped_column(Text)
    interview_notes: Mapped[str | None] = mapped_column(Text)
    application_notes: Mapped[str | None] = mapped_column(Text)

    organization: Mapped[Organization] = relationship(back_populates="applications")
    events: Mapped[list[ApplicationEvent]] = relationship(
        back_populates="application",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="ApplicationEvent.id",
    )

    __table_args__ = (
        Index("ix_applications_status_next_action", "current_status", "next_action_at"),
        Index("ix_applications_organization_status", "organization_id", "current_status"),
        Index("ix_applications_applied_at", "applied_at"),
        Index("ix_applications_archived_at", "archived_at"),
    )


class ApplicationEvent(Base):
    """A dated (or undated) entry in an Application's timeline."""

    __tablename__ = "application_events"

    id: Mapped[int] = mapped_column(primary_key=True)
    application_id: Mapped[int] = mapped_column(
        ForeignKey("applications.id", ondelete="CASCADE"), nullable=False
    )
    event_type: Mapped[ApplicationEventType] = mapped_column(
        _enum_column(ApplicationEventType, "application_event_type"), nullable=False
    )
    occurred_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    notes: Mapped[str | None] = mapped_column(Text)
    resulting_status: Mapped[ApplicationStatus | None] = mapped_column(
        _enum_column(ApplicationStatus, "application_event_result_status")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )

    application: Mapped[Application] = relationship(back_populates="events")

    __table_args__ = (
        Index("ix_application_events_application_occurred", "application_id", "occurred_at"),
    )
