"""Which JobTrack rows have already been imported, and as which new rows.

This is what makes the importer idempotent: a JobTrack row that already has a mapping is
skipped on later runs, so re-running against the same inputs creates nothing new.
"""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from sqlalchemy import DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from tracker.db import Base
from tracker.domain.models import utc_now


class ImportedEntity(StrEnum):
    ORGANIZATION = "organization"
    APPLICATION = "application"
    APPLICATION_EVENT = "application_event"


class JobTrackImportMapping(Base):
    """One imported JobTrack row: (entity, JobTrack id) -> id of the row it became."""

    __tablename__ = "jobtrack_import_map"

    entity: Mapped[str] = mapped_column(String(32), primary_key=True)
    jobtrack_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=False)
    new_id: Mapped[int] = mapped_column(Integer, nullable=False)
    imported_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )
