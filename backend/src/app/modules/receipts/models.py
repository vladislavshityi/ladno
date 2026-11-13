import uuid
from decimal import Decimal

from sqlalchemy import ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base, CreatedAt, UuidPk

MONEY = Numeric(14, 2)
RATE = Numeric(14, 4)


class Receipt(Base):
    __tablename__ = "receipts"

    id: Mapped[UuidPk]
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    period: Mapped[str | None] = mapped_column(String(7))
    uk_name: Mapped[str | None] = mapped_column(String(300))
    uk_inn: Mapped[str | None] = mapped_column(String(12))
    account_last4: Mapped[str | None] = mapped_column(String(4))
    area_m2: Mapped[Decimal | None] = mapped_column(RATE)
    residents: Mapped[int | None] = mapped_column(Integer)
    total: Mapped[Decimal] = mapped_column(MONEY)
    status: Mapped[str] = mapped_column(String(16))
    warnings: Mapped[list[str]] = mapped_column(JSONB, default=list)
    sample_id: Mapped[str | None] = mapped_column(String(40))
    created_at: Mapped[CreatedAt]

    lines: Mapped[list["ReceiptLine"]] = relationship(
        cascade="all, delete-orphan", order_by="ReceiptLine.id", lazy="selectin"
    )


class ReceiptLine(Base):
    __tablename__ = "receipt_lines"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    receipt_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("receipts.id", ondelete="CASCADE"), index=True
    )
    service_code: Mapped[str] = mapped_column(String(40))
    service_name: Mapped[str] = mapped_column(String(300))
    unit: Mapped[str | None] = mapped_column(String(20))
    volume: Mapped[Decimal | None] = mapped_column(RATE)
    tariff: Mapped[Decimal | None] = mapped_column(RATE)
    accrued: Mapped[Decimal] = mapped_column(MONEY)
    recalculation: Mapped[Decimal] = mapped_column(MONEY, default=Decimal("0"))
    total: Mapped[Decimal] = mapped_column(MONEY)
    method: Mapped[str] = mapped_column(String(16), default="unknown")
    explanation: Mapped[str | None] = mapped_column(Text)
