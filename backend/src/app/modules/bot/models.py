import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base, CreatedAt, UuidPk


class BotNotification(Base):
    """Сообщение жителю от бота; текст без ПД. Время отправки sent_at ставит бот."""

    __tablename__ = "bot_notifications"

    id: Mapped[UuidPk]
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    issue_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("issues.id", ondelete="CASCADE"))
    text: Mapped[str] = mapped_column(String(500))
    created_at: Mapped[CreatedAt]
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
