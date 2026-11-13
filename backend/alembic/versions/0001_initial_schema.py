"""initial schema

Revision ID: 0001
Revises:
Create Date: 2026-11-13 19:28:23.545799
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "management_companies",
        sa.Column("id", sa.Integer(), autoincrement=False, nullable=False),
        sa.Column("inn", sa.String(length=12), nullable=True),
        sa.Column("name", sa.String(length=300), nullable=False),
        sa.Column("phones", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("email", sa.String(length=200), nullable=True),
        sa.Column("emergency_phone", sa.String(length=50), nullable=True),
        sa.Column("site", sa.String(length=300), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_management_companies_inn"), "management_companies", ["inn"], unique=False
    )
    op.create_table(
        "houses",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("fias_id", sa.String(length=64), nullable=False),
        sa.Column("address", sa.String(length=500), nullable=False),
        sa.Column("lat", sa.Float(), nullable=True),
        sa.Column("lon", sa.Float(), nullable=True),
        sa.Column("district", sa.String(length=100), nullable=True),
        sa.Column("management_company_id", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(
            ["management_company_id"], ["management_companies.id"], ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("fias_id"),
    )
    op.create_table(
        "users",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("telegram_id", sa.BigInteger(), nullable=False),
        sa.Column("first_name", sa.String(length=100), nullable=True),
        sa.Column("house_id", sa.Integer(), nullable=True),
        sa.Column("full_name", sa.String(length=200), nullable=True),
        sa.Column("phone", sa.String(length=32), nullable=True),
        sa.Column("email", sa.String(length=200), nullable=True),
        sa.Column("apartment", sa.String(length=16), nullable=True),
        sa.Column("entrance", sa.String(length=8), nullable=True),
        sa.Column("management_company_id", sa.Integer(), nullable=True),
        sa.Column("consent_version", sa.String(length=32), nullable=True),
        sa.Column("consent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["house_id"], ["houses.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(
            ["management_company_id"], ["management_companies.id"], ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("telegram_id"),
    )
    op.create_table(
        "issues",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("category", sa.String(length=50), nullable=False),
        sa.Column("answers", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("already_contacted_uk", sa.Boolean(), nullable=False),
        sa.Column("house_id", sa.Integer(), nullable=True),
        sa.Column("location_details", sa.String(length=300), nullable=True),
        sa.Column("photo_ids", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("addressee_key", sa.String(length=50), nullable=False),
        sa.Column("route", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("escalation_level", sa.Integer(), nullable=False),
        sa.Column("parent_issue_id", sa.Uuid(), nullable=True),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("draft_full", sa.Text(), nullable=False),
        sa.Column("draft_pos_short", sa.Text(), nullable=False),
        sa.Column(
            "status",
            sa.Enum(
                "draft",
                "submitted",
                "in_progress",
                "resolved",
                "no_response",
                "rejected",
                name="issuestatus",
                native_enum=False,
                length=24,
            ),
            nullable=False,
        ),
        sa.Column("external_ref", sa.String(length=100), nullable=True),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deadline_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("reminder_sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["house_id"], ["houses.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["parent_issue_id"], ["issues.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_issues_category"), "issues", ["category"], unique=False)
    op.create_index(op.f("ix_issues_house_id"), "issues", ["house_id"], unique=False)
    op.create_index(op.f("ix_issues_status"), "issues", ["status"], unique=False)
    op.create_index(op.f("ix_issues_user_id"), "issues", ["user_id"], unique=False)
    op.create_table(
        "photos",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("path", sa.String(length=500), nullable=False),
        sa.Column("content_type", sa.String(length=50), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_photos_user_id"), "photos", ["user_id"], unique=False)
    op.create_table(
        "receipts",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("period", sa.String(length=7), nullable=True),
        sa.Column("uk_name", sa.String(length=300), nullable=True),
        sa.Column("uk_inn", sa.String(length=12), nullable=True),
        sa.Column("account_last4", sa.String(length=4), nullable=True),
        sa.Column("area_m2", sa.Numeric(precision=14, scale=4), nullable=True),
        sa.Column("residents", sa.Integer(), nullable=True),
        sa.Column("total", sa.Numeric(precision=14, scale=2), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("warnings", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("sample_id", sa.String(length=40), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_receipts_user_id"), "receipts", ["user_id"], unique=False)
    op.create_table(
        "receipt_lines",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("receipt_id", sa.Uuid(), nullable=False),
        sa.Column("service_code", sa.String(length=40), nullable=False),
        sa.Column("service_name", sa.String(length=300), nullable=False),
        sa.Column("unit", sa.String(length=20), nullable=True),
        sa.Column("volume", sa.Numeric(precision=14, scale=4), nullable=True),
        sa.Column("tariff", sa.Numeric(precision=14, scale=4), nullable=True),
        sa.Column("accrued", sa.Numeric(precision=14, scale=2), nullable=False),
        sa.Column("recalculation", sa.Numeric(precision=14, scale=2), nullable=False),
        sa.Column("total", sa.Numeric(precision=14, scale=2), nullable=False),
        sa.Column("method", sa.String(length=16), nullable=False),
        sa.Column("explanation", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["receipt_id"], ["receipts.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_receipt_lines_receipt_id"), "receipt_lines", ["receipt_id"], unique=False
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_receipt_lines_receipt_id"), table_name="receipt_lines")
    op.drop_table("receipt_lines")
    op.drop_index(op.f("ix_receipts_user_id"), table_name="receipts")
    op.drop_table("receipts")
    op.drop_index(op.f("ix_photos_user_id"), table_name="photos")
    op.drop_table("photos")
    op.drop_index(op.f("ix_issues_user_id"), table_name="issues")
    op.drop_index(op.f("ix_issues_status"), table_name="issues")
    op.drop_index(op.f("ix_issues_house_id"), table_name="issues")
    op.drop_index(op.f("ix_issues_category"), table_name="issues")
    op.drop_table("issues")
    op.drop_table("users")
    op.drop_table("houses")
    op.drop_index(op.f("ix_management_companies_inn"), table_name="management_companies")
    op.drop_table("management_companies")
