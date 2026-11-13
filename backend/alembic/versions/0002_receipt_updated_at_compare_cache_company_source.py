"""receipt updated_at, compare explanations cache, company source, custom address and company

Revision ID: 0002
Revises: 0001
Create Date: 2026-11-14 10:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("houses", sa.Column("management_company_source", sa.String(length=20)))
    op.add_column("users", sa.Column("custom_address", sa.String(length=500)))
    op.add_column("users", sa.Column("custom_company_name", sa.String(length=300)))
    op.add_column("issues", sa.Column("custom_address", sa.String(length=500)))
    op.add_column(
        "receipts",
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )
    op.create_table(
        "compare_explanations",
        sa.Column("base_id", sa.Uuid(), nullable=False),
        sa.Column("target_id", sa.Uuid(), nullable=False),
        sa.Column("base_updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("target_updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(["base_id"], ["receipts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["target_id"], ["receipts.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("base_id", "target_id"),
    )


def downgrade() -> None:
    op.drop_table("compare_explanations")
    op.drop_column("receipts", "updated_at")
    op.drop_column("issues", "custom_address")
    op.drop_column("users", "custom_company_name")
    op.drop_column("users", "custom_address")
    op.drop_column("houses", "management_company_source")
