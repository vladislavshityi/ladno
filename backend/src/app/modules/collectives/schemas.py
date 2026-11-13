import uuid
from datetime import datetime

from pydantic import BaseModel, Field, field_validator

from app.core.schemas import ApiModel
from app.modules.collectives.models import CollectiveStatus


class SimilarIssues(ApiModel):
    count: int = Field(description="Сколько других жителей дома сообщили о такой же проблеме")
    collective_id: uuid.UUID | None = Field(
        None, description="Открытое коллективное обращение по этой проблеме, если оно уже есть"
    )


class JoinRequest(BaseModel):
    issue_id: uuid.UUID = Field(description="Своё обращение, с которым житель присоединяется")
    consent: bool = Field(description="Согласие на участие в коллективном обращении, только true")
    consent_letter: bool = Field(
        False, description="Согласие указать ФИО и квартиру в коллективном письме"
    )

    @field_validator("consent")
    @classmethod
    def _must_agree(cls, value: bool) -> bool:
        if not value:
            raise ValueError("Нужно согласие на участие в коллективном обращении")
        return value


class MembershipPatch(BaseModel):
    consent_letter: bool


class CollectiveRead(ApiModel):
    """Соседям видно только число участников: имена и квартиры не раскрываются."""

    id: uuid.UUID
    house_id: int
    address: str
    category: str
    category_title: str
    status: CollectiveStatus
    members_count: int
    my_issue_id: uuid.UUID | None = None
    consent_letter: bool = Field(description="Согласие текущего жителя на ФИО и квартиру в письме")
    created_at: datetime
    submitted_at: datetime | None = None


class CollectiveLetter(ApiModel):
    text: str
    members_count: int
