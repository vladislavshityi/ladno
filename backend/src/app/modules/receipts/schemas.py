import uuid
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field

from app.core.schemas import ApiModel, Money, ORMModel

ServiceCode = Literal[
    "maintenance", "cold_water", "hot_water", "hot_water_heat", "sewerage", "heating",
    "electricity", "gas", "waste", "capital_repair", "common_property_resources",
    "intercom", "other",
]  # fmt: skip
CalcMethod = Literal["meter", "norm", "norm_increased", "unknown"]
ReceiptStatus = Literal["parsed", "needs_review"]
FindingType = Literal[
    "tariff_mismatch",
    "norm_instead_of_meter",
    "norm_increased",
    "duplicate_line",
    "unexplained_recalculation",
]
LineFlag = Literal[
    "growth_over_15pct", "new_line", "removed_line", "switched_to_norm",
    "norm_increased", "has_recalculation", "has_penalty", "tariff_changed",
]  # fmt: skip
CompareFlag = Literal["heating_season_start", "tariff_indexation"]


class ReceiptCompany(ApiModel):
    name: str | None = None
    inn: str | None = None


class ReceiptLine(ORMModel):
    id: int
    service_code: ServiceCode
    service_name: str
    unit: str | None = None
    volume: Money | None = None
    tariff: Money | None = None
    accrued: Money
    recalculation: Money
    total: Money
    method: CalcMethod = "unknown"
    explanation: str | None = Field(None, description="Что это за строка, простым языком")


class Receipt(ApiModel):
    id: uuid.UUID
    status: ReceiptStatus
    period: str | None = Field(None, description="YYYY-MM; пусто, если период не распознан")
    management_company: ReceiptCompany | None = None
    account_last4: str | None = Field(None, description="Лицевой счёт хранится только маской")
    area_m2: Money | None = None
    residents: int | None = None
    lines: list[ReceiptLine] = []
    total: Money
    warnings: list[str] = Field([], description="Что не сошлось и нужно проверить вручную")


class ReceiptShort(ORMModel):
    id: uuid.UUID
    period: str | None = None
    total: Money
    status: ReceiptStatus


class ReceiptSample(ApiModel):
    id: str
    title: str


class LinePatch(BaseModel):
    volume: Money | None = None
    tariff: Money | None = None
    accrued: Money | None = None


class ParsedLine(BaseModel):
    service_code: ServiceCode = "other"
    service_name: str
    unit: str | None = None
    volume: Money | None = None
    tariff: Money | None = None
    accrued: Money
    recalculation: Money = Decimal("0")
    total: Money | None = None
    method: CalcMethod = "unknown"


class ParsedReceipt(BaseModel):
    """Результат разбора квитанции (из демо-образца или от модели) до сохранения."""

    period: str | None = None
    management_company: ReceiptCompany | None = None
    account_last4: str | None = None
    area_m2: Money | None = None
    residents: int | None = None
    lines: list[ParsedLine] = []
    total: Money | None = None
    warnings: list[str] = []  # что не удалось прочитать при разборе


class ManualCompany(BaseModel):
    name: str | None = Field(None, max_length=200)
    inn: str | None = Field(None, pattern=r"^\d{10}(\d{2})?$")


class ManualReceipt(BaseModel):
    """Квитанция, введённая жителем вручную. Полный лицевой счёт и ФИО не принимаются."""

    period: str = Field(pattern=r"^\d{4}-(0[1-9]|1[0-2])$", description="YYYY-MM")
    management_company: ManualCompany | None = None
    account_last4: str | None = Field(None, pattern=r"^\d{4}$", description="Последние 4 цифры")
    area_m2: Money | None = None
    residents: int | None = Field(None, ge=0, le=99)
    lines: list[ParsedLine] = Field(min_length=1, max_length=50)
    total: Money | None = Field(None, description="Итог к оплате; пусто — сумма строк")


class ServiceOption(ApiModel):
    service_code: ServiceCode
    name: str
    unit: str | None = None
    tariff: Money | None = Field(
        None, description="Тариф региона на период в единицах строки; пусто, если неоднозначен"
    )


class CompareLine(ApiModel):
    service_code: ServiceCode
    service_name: str
    accrued_base: Money
    accrued_target: Money
    delta: Money
    delta_pct: Money | None = None
    delta_tariff: Money
    delta_volume: Money
    delta_other: Money
    flags: list[LineFlag] = []


class Compare(ApiModel):
    base_period: str
    target_period: str
    total_base: Money
    total_target: Money
    total_delta: Money
    lines: list[CompareLine] = []
    flags: list[CompareFlag] = []


class CompareExplanation(ApiModel):
    text: str = Field(description="Почему изменилась сумма; частично пишет языковая модель")


class Finding(ApiModel):
    type: FindingType
    service_code: ServiceCode
    title: str
    description: str
    possible_overpayment: Money
    confidence: Literal["high", "medium", "low"]


class Check(ApiModel):
    findings: list[Finding] = []
    total_possible_overpayment: Money


class RecalculationLetterRequest(BaseModel):
    finding_types: list[FindingType] = Field(
        [], description="По каким нарушениям просить перерасчёт; пусто — по всем найденным"
    )


class RecalculationLetter(ApiModel):
    text: str = Field(
        description="Текст заявления; ФИО, квартира и телефон — метки для подстановки"
    )
