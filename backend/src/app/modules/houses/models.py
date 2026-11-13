from sqlalchemy import Float, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base


class ManagementCompany(Base):
    __tablename__ = "management_companies"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=False)
    inn: Mapped[str | None] = mapped_column(String(12), index=True)
    name: Mapped[str] = mapped_column(String(300))
    phones: Mapped[list[str]] = mapped_column(JSONB, default=list)
    email: Mapped[str | None] = mapped_column(String(200))
    emergency_phone: Mapped[str | None] = mapped_column(String(50))
    site: Mapped[str | None] = mapped_column(String(300))


class House(Base):
    __tablename__ = "houses"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    fias_id: Mapped[str] = mapped_column(String(64), unique=True)
    address: Mapped[str] = mapped_column(String(500))
    lat: Mapped[float | None] = mapped_column(Float)
    lon: Mapped[float | None] = mapped_column(Float)
    district: Mapped[str | None] = mapped_column(String(100))
    management_company_id: Mapped[int | None] = mapped_column(
        ForeignKey("management_companies.id", ondelete="SET NULL")
    )
    management_company_source: Mapped[str | None] = mapped_column(String(20))

    management_company: Mapped[ManagementCompany | None] = relationship(lazy="joined")
