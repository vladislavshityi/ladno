import uuid
from enum import StrEnum

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base, CreatedAt, UuidPk, str_enum


class AttemptStatus(StrEnum):
    SENT = "sent"
    FAILED = "failed"


class SubmissionAttempt(Base):
    """Одна попытка автоматической отправки обращения адресату."""

    __tablename__ = "submission_attempts"

    id: Mapped[UuidPk]
    issue_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("issues.id", ondelete="CASCADE"), index=True
    )
    channel: Mapped[str] = mapped_column(String(24))
    status: Mapped[AttemptStatus] = mapped_column(str_enum(AttemptStatus))
    external_ref: Mapped[str | None] = mapped_column(String(200))
    error: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[CreatedAt]
