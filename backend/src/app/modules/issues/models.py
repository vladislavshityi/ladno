import uuid
from datetime import datetime
from enum import StrEnum
from typing import Any

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base, CreatedAt, UuidPk, str_enum
from app.modules.houses.models import House


class IssueStatus(StrEnum):
    DRAFT = "draft"
    SUBMITTED = "submitted"
    IN_PROGRESS = "in_progress"
    RESOLVED = "resolved"
    NO_RESPONSE = "no_response"
    REJECTED = "rejected"


ACTIVE_STATUSES = (IssueStatus.SUBMITTED, IssueStatus.IN_PROGRESS)
# Адресат дал ответ по существу: решил проблему или отказал.
ANSWERED_STATUSES = (IssueStatus.RESOLVED, IssueStatus.REJECTED)


class Photo(Base):
    __tablename__ = "photos"

    id: Mapped[UuidPk]
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    path: Mapped[str] = mapped_column(String(500))
    content_type: Mapped[str] = mapped_column(String(50))
    created_at: Mapped[CreatedAt]


class Issue(Base):
    __tablename__ = "issues"

    id: Mapped[UuidPk]
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    category: Mapped[str] = mapped_column(String(50), index=True)
    answers: Mapped[dict[str, str]] = mapped_column(JSONB, default=dict)
    already_contacted_uk: Mapped[bool] = mapped_column(Boolean, default=False)
    house_id: Mapped[int | None] = mapped_column(
        ForeignKey("houses.id", ondelete="SET NULL"), index=True
    )
    custom_address: Mapped[str | None] = mapped_column(String(500))
    location_details: Mapped[str | None] = mapped_column(String(300))
    description: Mapped[str] = mapped_column(Text, default="", server_default="")
    photo_ids: Mapped[list[str]] = mapped_column(JSONB, default=list)

    addressee_key: Mapped[str] = mapped_column(String(50))
    route: Mapped[dict[str, Any]] = mapped_column(JSONB)
    escalation_level: Mapped[int] = mapped_column(Integer, default=0)
    parent_issue_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("issues.id", ondelete="SET NULL")
    )

    summary: Mapped[str] = mapped_column(Text, default="")
    draft_full: Mapped[str] = mapped_column(Text, default="")
    draft_pos_short: Mapped[str] = mapped_column(Text, default="")

    status: Mapped[IssueStatus] = mapped_column(
        str_enum(IssueStatus), default=IssueStatus.DRAFT, index=True
    )
    external_ref: Mapped[str | None] = mapped_column(String(100))
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    deadline_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    # Когда обращение получило ответ (решено или отказ): по нему считается рейтинг УК.
    answered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    reminder_sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[CreatedAt]

    house: Mapped[House | None] = relationship(lazy="joined")
