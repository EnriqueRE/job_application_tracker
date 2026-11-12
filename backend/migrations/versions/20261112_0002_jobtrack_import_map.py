"""JobTrack import mapping: which JobTrack rows were imported as which new rows.

Revision ID: 0002
Revises: 0001
Create Date: 2026-11-12 16:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0002"
down_revision: str | Sequence[str] | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "jobtrack_import_map",
        sa.Column("entity", sa.String(length=32), nullable=False),
        sa.Column("jobtrack_id", sa.Integer(), autoincrement=False, nullable=False),
        sa.Column("new_id", sa.Integer(), nullable=False),
        sa.Column("imported_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("entity", "jobtrack_id", name=op.f("pk_jobtrack_import_map")),
    )


def downgrade() -> None:
    op.drop_table("jobtrack_import_map")
