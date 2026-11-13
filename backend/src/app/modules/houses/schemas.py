from pydantic import Field

from app.core.schemas import ORMModel


class ManagementCompanyRead(ORMModel):
    id: int
    name: str
    inn: str | None = None
    phones: list[str] = Field(default_factory=list)
    emergency_phone: str | None = None
    email: str | None = None
    site: str | None = None


class HouseRead(ORMModel):
    id: int
    address: str
    district: str | None = None
    lat: float | None = None
    lon: float | None = None
    management_company: ManagementCompanyRead | None = None


class AddressSuggestion(ORMModel):
    house_id: int
    address: str
    lat: float | None = None
    lon: float | None = None
