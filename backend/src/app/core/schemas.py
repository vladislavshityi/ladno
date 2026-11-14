from decimal import Decimal
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, PlainSerializer


class ApiModel(BaseModel):
    """База схем ответов: поля с default сервер отдаёт всегда, в OpenAPI они обязательны."""

    model_config = ConfigDict(json_schema_serialization_defaults_required=True)


class ORMModel(ApiModel):
    model_config = ConfigDict(from_attributes=True)


class ErrorResponse(ApiModel):
    detail: str
    code: str
    fields: dict[str, str] = Field(
        default_factory=dict,
        description="Ошибки проверки по полям (для 422): путь к полю -> сообщение",
    )


# В JSON деньги и объёмы — строки с точкой, чтобы не терять точность во float.
Money = Annotated[
    Decimal, PlainSerializer(lambda v: format(v, "f"), return_type=str, when_used="json")
]
