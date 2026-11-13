import uuid
from datetime import datetime
from typing import Literal, Self

from pydantic import BaseModel, Field, model_validator

from app.core.schemas import Money, ORMModel
from app.modules.issues.models import IssueStatus

ChannelType = Literal["phone", "email", "url", "pos", "gis_zhkh", "telegram"]
DeadlineType = Literal["working", "calendar"]


class Category(BaseModel):
    id: str
    title: str
    icon: str
    pos_hint: str = Field(description="Рубрика на платформе «Решаем вместе», куда подать обращение")


class QuestionOption(BaseModel):
    value: str
    label: str


class Question(BaseModel):
    id: str
    text: str
    options: list[QuestionOption]


class ClassifyRequest(BaseModel):
    text: str = Field("", max_length=1000, description="Описание проблемы своими словами")
    photo_ids: list[uuid.UUID] = Field(
        [], max_length=3, description="Загруженные фото проблемы (POST /photos)"
    )

    @model_validator(mode="after")
    def _needs_input(self) -> Self:
        if len(self.text.strip()) < 3 and not self.photo_ids:
            raise ValueError("Нужно описание проблемы или фото")
        return self


class Contact(BaseModel):
    type: ChannelType
    value: str
    label: str


class Emergency(BaseModel):
    reason: str
    contacts: list[Contact] = []


class Classification(BaseModel):
    category: str | None = Field(None, description="Категория из справочника региона")
    confidence: float = Field(0.0, ge=0, le=1)
    summary: str = ""
    needs_manual_choice: bool = Field(
        False, description="Категорию не удалось определить: предложите выбрать вручную"
    )
    clarification: str | None = Field(
        None, description="Если данных мало: что стоит уточнить, чтобы определить проблему"
    )
    is_emergency: bool = False
    emergency: Emergency | None = None


class Channel(BaseModel):
    type: ChannelType
    value: str
    label: str


class Addressee(BaseModel):
    key: str
    name: str
    kind: str
    channels: list[Channel] = []


class Basis(BaseModel):
    text: str
    source: str
    verified: bool = False


class Deadline(BaseModel):
    days: int
    type: DeadlineType
    source: str
    verified: bool = False


class EscalationStep(BaseModel):
    key: str
    name: str


class RecalculationHint(BaseModel):
    service_name: str
    monthly_amount: Money


class RouteRequest(BaseModel):
    category: str
    answers: dict[str, str] = {}
    already_contacted_uk: bool = False


class RouteResult(BaseModel):
    addressee: Addressee
    explanation: str = ""
    basis: list[Basis] = []
    fix_deadline: Deadline | None = None
    response_deadline: Deadline | None = None
    escalation: list[EscalationStep] = []
    recalculation_hint: RecalculationHint | None = Field(
        None, description="Если адресат — УК и есть квитанция: услуга, по которой просят перерасчёт"
    )


class IssueCreate(BaseModel):
    category: str
    answers: dict[str, str] = {}
    already_contacted_uk: bool = False
    house_id: int | None = Field(None, description="Дом; по умолчанию дом из профиля")
    location_details: str | None = Field(None, max_length=300, description="Подъезд, этаж, место")
    photo_ids: list[uuid.UUID] = Field([], max_length=10)


class Draft(BaseModel):
    full: str = ""
    pos_short: str = ""


class IssuePatch(BaseModel):
    status: IssueStatus | None = None
    external_ref: str | None = Field(None, max_length=100)
    submitted_at: datetime | None = None
    draft: Draft | None = None


class IssuePhoto(BaseModel):
    id: uuid.UUID
    url: str


class IssueRead(ORMModel):
    id: uuid.UUID
    category: str
    category_title: str
    status: IssueStatus
    house_id: int | None = None
    address: str | None = None
    location_details: str | None = None
    photos: list[IssuePhoto] = Field(default_factory=list)
    route: RouteResult
    escalation_level: int = 0
    parent_issue_id: uuid.UUID | None = None
    draft: Draft
    external_ref: str | None = None
    submitted_at: datetime | None = None
    deadline_at: datetime | None = None
    is_overdue: bool = False
    created_at: datetime


class SubmissionAlternative(BaseModel):
    channel: Literal["gis_zhkh_link", "email_copy"]
    open_url: str
    label: str


class Submission(BaseModel):
    channel: Literal["pos_link"] = "pos_link"
    text: str = Field(description="Короткий текст для вставки в форму")
    char_limit: int
    open_url: str
    category_hint: str | None = None
    steps: list[str] = []
    alternatives: list[SubmissionAlternative] = []


class PhotoRead(BaseModel):
    id: uuid.UUID
    url: str
