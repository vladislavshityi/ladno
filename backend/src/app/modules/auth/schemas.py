from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.core.schemas import ApiModel
from app.modules.users.schemas import UserRead


class AuthConfig(ApiModel):
    telegram_bot_username: str = Field(description="Имя бота для Telegram Login Widget, без @")
    dev_login_enabled: bool = Field(
        description="Доступен ли вход без Telegram (только APP_ENV=dev)"
    )
    consent_version: str = Field(description="Текущая версия согласия на обработку данных")


class TelegramWidgetLogin(BaseModel):
    """Данные, которые Telegram Login Widget отдаёт странице; hash проверяется на сервере."""

    model_config = ConfigDict(extra="allow")

    id: int
    first_name: str | None = None
    last_name: str | None = None
    username: str | None = None
    photo_url: str | None = None
    auth_date: int
    hash: str


class TelegramWebAppLogin(BaseModel):
    init_data: str = Field(description="Строка Telegram.WebApp.initData целиком")


class DevLogin(BaseModel):
    telegram_id: int = Field(1, description="Условный Telegram id тестового пользователя")
    first_name: str | None = "Тест"


class TokenResponse(ApiModel):
    access_token: str
    token_type: Literal["bearer"] = "bearer"
    user: UserRead
