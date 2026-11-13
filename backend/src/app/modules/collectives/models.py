import uuid
from datetime import datetime
from enum import StrEnum

from sqlalchemy import Boolean, DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base, CreatedAt, UuidPk, str_enum, utcnow


class CollectiveStatus(StrEnum):
    OPEN = "open"
    SUBMITTED = "submitted"
    CLOSED = "closed"


class CollectiveIssue(Base):
    """Жильцы одного дома с одной проблемой: объединённое обращение."""

    __tablename__ = "collective_issues"

    id: Mapped[UuidPk]
    house_id: Mapped[int] = mapped_column(ForeignKey("houses.id", ondelete="CASCADE"), index=True)
    category: Mapped[str] = mapped_column(String(50))
    # Самое раннее похожее обращение: по его маршруту и описанию строится общее письмо.
    initiator_issue_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("issues.id", ondelete="SET NULL")
    )
    status: Mapped[CollectiveStatus] = mapped_column(
        str_enum(CollectiveStatus), default=CollectiveStatus.OPEN
    )
    created_at: Mapped[CreatedAt]
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class CollectiveMember(Base):
    __tablename__ = "collective_members"

    collective_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("collective_issues.id", ondelete="CASCADE"), primary_key=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True, index=True
    )
    issue_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("issues.id", ondelete="SET NULL"))
    # Согласие указать ФИО и квартиру в общем письме; без него участник входит в письмо числом.
    consent_letter: Mapped[bool] = mapped_column(Boolean, default=False)
    joined_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, server_default=func.now()
    )
