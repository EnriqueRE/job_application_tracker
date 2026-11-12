"""Baseline domain schema: organizations, applications, application_events.

Revision ID: 0001
Revises:
Create Date: 2026-11-12 10:15:25.515861

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0001"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "organizations",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column(
            "organization_type",
            sa.Enum(
                "company",
                "recruiter",
                "recruiting_firm",
                "portal",
                name="organization_type",
                native_enum=False,
                create_constraint=True,
            ),
            nullable=False,
        ),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("normalized_name", sa.String(length=255), nullable=False),
        sa.Column("industry", sa.String(length=128), nullable=True),
        sa.Column("location", sa.String(length=255), nullable=True),
        sa.Column("priority", sa.Integer(), nullable=False),
        sa.Column("website_url", sa.Text(), nullable=True),
        sa.Column("career_url", sa.Text(), nullable=True),
        sa.Column("contact_url", sa.Text(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "priority BETWEEN 0 AND 5", name=op.f("ck_organizations_priority_range")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_organizations")),
        sa.UniqueConstraint(
            "organization_type", "normalized_name", name="organization_type_normalized_name"
        ),
    )
    op.create_index("ix_organizations_archived_at", "organizations", ["archived_at"], unique=False)
    op.create_index(
        "ix_organizations_type_name",
        "organizations",
        ["organization_type", "normalized_name"],
        unique=False,
    )
    op.create_table(
        "applications",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("organization_id", sa.Integer(), nullable=False),
        sa.Column("role", sa.String(length=255), nullable=False),
        sa.Column("location", sa.String(length=255), nullable=True),
        sa.Column(
            "work_arrangement",
            sa.Enum(
                "remote",
                "hybrid",
                "onsite",
                "unspecified",
                name="work_arrangement",
                native_enum=False,
                create_constraint=True,
            ),
            nullable=False,
        ),
        sa.Column("vacancy_source", sa.String(length=255), nullable=True),
        sa.Column("vacancy_url", sa.Text(), nullable=True),
        sa.Column("vacancy_age", sa.String(length=128), nullable=True),
        sa.Column("applied_at", sa.Date(), nullable=True),
        sa.Column(
            "current_status",
            sa.Enum(
                "saved",
                "applied",
                "screening",
                "interview",
                "technical_interview",
                "final_interview",
                "offer",
                "rejected",
                "withdrawn",
                "closed",
                "no_response",
                name="application_status",
                native_enum=False,
                create_constraint=True,
            ),
            nullable=False,
        ),
        sa.Column("next_action_at", sa.Date(), nullable=True),
        sa.Column("status_overridden", sa.Boolean(), nullable=False),
        sa.Column("job_description", sa.Text(), nullable=True),
        sa.Column("interview_notes", sa.Text(), nullable=True),
        sa.Column("application_notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
            name=op.f("fk_applications_organization_id_organizations"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_applications")),
    )
    op.create_index("ix_applications_applied_at", "applications", ["applied_at"], unique=False)
    op.create_index("ix_applications_archived_at", "applications", ["archived_at"], unique=False)
    op.create_index(
        "ix_applications_organization_status",
        "applications",
        ["organization_id", "current_status"],
        unique=False,
    )
    op.create_index(
        "ix_applications_status_next_action",
        "applications",
        ["current_status", "next_action_at"],
        unique=False,
    )
    op.create_table(
        "application_events",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("application_id", sa.Integer(), nullable=False),
        sa.Column(
            "event_type",
            sa.Enum(
                "saved",
                "applied",
                "contacted",
                "screening",
                "interview_scheduled",
                "interview_completed",
                "technical_interview",
                "final_interview",
                "follow_up",
                "offer",
                "rejected",
                "withdrawn",
                "closed",
                "no_response",
                "note",
                name="application_event_type",
                native_enum=False,
                create_constraint=True,
            ),
            nullable=False,
        ),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column(
            "resulting_status",
            sa.Enum(
                "saved",
                "applied",
                "screening",
                "interview",
                "technical_interview",
                "final_interview",
                "offer",
                "rejected",
                "withdrawn",
                "closed",
                "no_response",
                name="application_event_result_status",
                native_enum=False,
                create_constraint=True,
            ),
            nullable=True,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["application_id"],
            ["applications.id"],
            name=op.f("fk_application_events_application_id_applications"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_application_events")),
    )
    op.create_index(
        "ix_application_events_application_occurred",
        "application_events",
        ["application_id", "occurred_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_application_events_application_occurred", table_name="application_events")
    op.drop_table("application_events")
    op.drop_index("ix_applications_status_next_action", table_name="applications")
    op.drop_index("ix_applications_organization_status", table_name="applications")
    op.drop_index("ix_applications_archived_at", table_name="applications")
    op.drop_index("ix_applications_applied_at", table_name="applications")
    op.drop_table("applications")
    op.drop_index("ix_organizations_type_name", table_name="organizations")
    op.drop_index("ix_organizations_archived_at", table_name="organizations")
    op.drop_table("organizations")
