import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from app.core.schemas import ORMModel
from app.modules.houses.schemas import HouseRead, ManagementCompanyRead
from app.modules.issues.schemas import IssueRead, PhotoRead
from app.modules.receipts.schemas import Receipt


class UserRead(ORMModel):
    id: uuid.UUID
    first_name: str | None = Field(None, description="Имя из Telegram для обращения к жителю")
    house: HouseRead | None = None
    entrance: str | None = None
    management_company: ManagementCompanyRead | None = None
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
    entrance: str | None = Field(None, max_length=8)
    full_name: str | None = Field(None, max_length=200, description="Подставляется в письма кодом")
    phone: str | None = Field(None, max_length=32)
    email: str | None = Field(None, max_length=200)
    apartment: str | None = Field(None, max_length=16)
    management_company_id: int | None = Field(
        None, description="Если не задана, берётся УК дома из справочника"
    )


class ConsentRequest(BaseModel):
    version: str = Field(description="Версия текста согласия, которую увидел житель")


class UserExport(BaseModel):
    """Все данные пользователя одним JSON."""

    profile: UserRead
    issues: list[IssueRead]
    receipts: list[Receipt]
    photos: list[PhotoRead]
