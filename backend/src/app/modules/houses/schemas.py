from typing import Literal

from pydantic import Field, model_validator

from app.core.schemas import ORMModel

CompanySource = Literal["gis_zhkh", "vl_ru"]


class ManagementCompanyRead(ORMModel):
    id: int
    name: str
    inn: str | None = None
    phones: list[str] = Field(default_factory=list)
    emergency_phone: str | None = None
    email: str | None = None
    site: str | None = None
    source: CompanySource | None = Field(
        None, description="Откуда известна связка дома с УК; пусто, если УК выбрана жителем"
    )


class HouseRead(ORMModel):
    id: int
    address: str
    district: str | None = None
    lat: float | None = None
    lon: float | None = None
    management_company: ManagementCompanyRead | None = None
    management_company_source: CompanySource | None = Field(None, exclude=True)

    @model_validator(mode="after")
    def _company_source(self) -> "HouseRead":
        if self.management_company:
            self.management_company.source = self.management_company_source
        return self


class AddressSuggestion(ORMModel):
    house_id: int
    address: str
    lat: float | None = None
    lon: float | None = None
