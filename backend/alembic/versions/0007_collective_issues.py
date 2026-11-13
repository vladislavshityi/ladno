"""collective issues and bot notifications

Revision ID: 0007
Revises: 0006
Create Date: 2026-11-17 12:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0007"
down_revision: str | None = "0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

NOW = sa.text("now()")


def upgrade() -> None:
    op.create_table(
        "collective_issues",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("house_id", sa.Integer(), nullable=False),
        sa.Column("category", sa.String(length=50), nullable=False),
        sa.Column("initiator_issue_id", sa.Uuid(), nullable=True),
        sa.Column("status", sa.String(length=24), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=NOW, nullable=False),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["house_id"], ["houses.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["initiator_issue_id"], ["issues.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_collective_issues_house_id"), "collective_issues", ["house_id"], unique=False
    )
    op.create_table(
        "collective_members",
        sa.Column("collective_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("issue_id", sa.Uuid(), nullable=True),
        sa.Column("consent_letter", sa.Boolean(), nullable=False),
        sa.Column("joined_at", sa.DateTime(timezone=True), server_default=NOW, nullable=False),
        sa.ForeignKeyConstraint(["collective_id"], ["collective_issues.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["issue_id"], ["issues.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("collective_id", "user_id"),
    )
    op.create_index(
        op.f("ix_collective_members_user_id"), "collective_members", ["user_id"], unique=False
    )
    op.add_column("issues", sa.Column("collective_id", sa.Uuid(), nullable=True))
    op.create_foreign_key(
        "fk_issues_collective_id",
        "issues",
        "collective_issues",
        ["collective_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_table(
        "bot_notifications",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("issue_id", sa.Uuid(), nullable=False),
        sa.Column("text", sa.String(length=500), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=NOW, nullable=False),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["issue_id"], ["issues.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("bot_notifications")
    op.drop_constraint("fk_issues_collective_id", "issues", type_="foreignkey")
    op.drop_column("issues", "collective_id")
    op.drop_index(op.f("ix_collective_members_user_id"), table_name="collective_members")
    op.drop_table("collective_members")
    op.drop_index(op.f("ix_collective_issues_house_id"), table_name="collective_issues")
    op.drop_table("collective_issues")
