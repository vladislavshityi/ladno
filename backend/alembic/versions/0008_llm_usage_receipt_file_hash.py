"""llm usage counters and receipt file hash

Revision ID: 0008
Revises: 0007
Create Date: 2026-11-20 12:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0008"
down_revision: str | None = "0007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "llm_usage",
        sa.Column("window", sa.DateTime(timezone=True), nullable=False),
        sa.Column("kind", sa.String(length=24), nullable=False),
        sa.Column("subject", sa.String(length=36), nullable=False),
        sa.Column("requests", sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint("window", "kind", "subject"),
    )
    op.add_column("receipts", sa.Column("file_hash", sa.String(length=64), nullable=True))
    op.create_index(op.f("ix_receipts_file_hash"), "receipts", ["file_hash"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_receipts_file_hash"), table_name="receipts")
    op.drop_column("receipts", "file_hash")
    op.drop_table("llm_usage")
