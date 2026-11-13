"""encrypt user personal data

Revision ID: 0003
Revises: 0002
Create Date: 2026-11-14 12:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

from app.core.crypto import EncryptedString

revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

COLUMNS = ("full_name", "phone", "email", "apartment", "entrance", "custom_address")


def upgrade() -> None:
    for column in COLUMNS:
        op.alter_column("users", column, type_=sa.Text())

    # Уже сохранённые значения шифруются тем же ключом, что и новые записи.
    cipher = EncryptedString()
    conn = op.get_bind()
    rows = conn.execute(sa.text(f"SELECT id, {', '.join(COLUMNS)} FROM users")).mappings()
    for row in rows.all():
        values = {c: cipher.process_bind_param(row[c], None) for c in COLUMNS}
        assignments = ", ".join(f"{c} = :{c}" for c in COLUMNS)
        conn.execute(
            sa.text(f"UPDATE users SET {assignments} WHERE id = :id"), {**values, "id": row["id"]}
        )


def downgrade() -> None:
    raise NotImplementedError("Расшифровка обратно в открытый вид не поддерживается")
