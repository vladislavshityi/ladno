import uuid
from datetime import datetime
from typing import Self

from pydantic import BaseModel, Field, field_validator, model_validator

from app.core.schemas import ApiModel, ORMModel
from app.modules.houses.schemas import HouseRead, ManagementCompanyRead
from app.modules.issues.schemas import IssueRead, PhotoRead
from app.modules.receipts.schemas import Receipt


class UserRead(ORMModel):
    id: uuid.UUID
    first_name: str | None = Field(None, description="Имя из Telegram для обращения к жителю")
    house: HouseRead | None = None
    entrance: str | None = None
    custom_address: str | None = Field(None, description="Адрес, которого нет в справочнике")
    management_company: ManagementCompanyRead | None = None
    custom_company_name: str | None = Field(None, description="УК или ТСЖ, которых нет в списке")
    full_name: str | None = None
    phone: str | None = None
    email: str | None = None
    apartment: str | None = None
    consent_version: str | None = None
    consent_at: datetime | None = None
    consent_required: bool = Field(
        True, description="Нужно показать согласие на обработку данных и отправить POST /consent"
    )


class ProfileUpdate(BaseModel):
    house_id: int | None = Field(None, description="Дом из поиска адреса")
    custom_address: str | None = Field(
        None, max_length=500, description="Адрес, если дома нет в справочнике; вместо house_id"
    )
    entrance: str | None = Field(None, max_length=8)
    full_name: str | None = Field(None, max_length=200, description="Подставляется в письма кодом")
    phone: str | None = Field(None, max_length=32)
    email: str | None = Field(None, max_length=200)
    apartment: str | None = Field(None, max_length=16)
    management_company_id: int | None = Field(
        None, description="Если не задана, берётся УК дома из справочника"
    )
    custom_company_name: str | None = Field(
        None,
        max_length=300,
        description="УК или ТСЖ, которых нет в списке; вместо management_company_id",
    )

    @field_validator("custom_address", "custom_company_name")
    @classmethod
    def _blank_is_none(cls, value: str | None) -> str | None:
        return (value or "").strip() or None

    @model_validator(mode="after")
    def _one_of_pair(self) -> Self:
        if self.house_id is not None and self.custom_address:
            raise ValueError("Укажите либо house_id, либо custom_address")
        if self.management_company_id is not None and self.custom_company_name:
            raise ValueError("Укажите либо management_company_id, либо custom_company_name")
        return self


class ConsentRequest(BaseModel):
    version: str = Field(description="Версия текста согласия, которую увидел житель")


class UserExport(ApiModel):
    """Все данные пользователя одним JSON."""

    profile: UserRead
    issues: list[IssueRead]
    receipts: list[Receipt]
    photos: list[PhotoRead]
