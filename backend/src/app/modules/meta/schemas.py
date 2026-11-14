from pydantic import Field

from app.core.schemas import ApiModel
from app.modules.issues.schemas import Basis


class Meta(ApiModel):
    llm: bool = Field(description="Подключена языковая модель: доступен ассистент")
    vision: bool = Field(description="Модель понимает изображения: разбор фото квитанций")
    region: str
    demo_data: bool = Field(description="Данные демонстрационные")
    llm_fallbacks: dict[str, int] = Field(
        description="Сколько раз по месту вызова модель не помогла и взят запасной путь"
    )
    llm_budget_exhausted: bool = Field(
        description="Суточный бюджет запросов к модели исчерпан: до 00:00 UTC работают шаблоны"
    )
    llm_tokens_today: int = Field(
        description="Токенов израсходовано за сутки с запуска сервиса; только статистика"
    )


class FaqItem(ApiModel):
    id: str
    question: str
    answer: str
    basis: list[Basis] = []
