from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.crypto import EncryptedString
from app.core.db import Base, CreatedAt, UuidPk
from app.modules.houses.models import House, ManagementCompany


class User(Base):
    __tablename__ = "users"

    id: Mapped[UuidPk]
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True)
    first_name: Mapped[str | None] = mapped_column(String(100))
    house_id: Mapped[int | None] = mapped_column(ForeignKey("houses.id", ondelete="SET NULL"))
    full_name: Mapped[str | None] = mapped_column(EncryptedString)
    phone: Mapped[str | None] = mapped_column(EncryptedString)
    email: Mapped[str | None] = mapped_column(EncryptedString)
    apartment: Mapped[str | None] = mapped_column(EncryptedString)
    entrance: Mapped[str | None] = mapped_column(EncryptedString)
    custom_address: Mapped[str | None] = mapped_column(EncryptedString)
    custom_company_name: Mapped[str | None] = mapped_column(String(300))
    management_company_id: Mapped[int | None] = mapped_column(
        ForeignKey("management_companies.id", ondelete="SET NULL")
    )
    consent_version: Mapped[str | None] = mapped_column(String(32))
    consent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[CreatedAt]

    house: Mapped[House | None] = relationship(lazy="joined")
    management_company: Mapped[ManagementCompany | None] = relationship(lazy="joined")
