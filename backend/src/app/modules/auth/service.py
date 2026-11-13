import time

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.errors import NotFound, ServiceUnavailable, Unauthorized
from app.core.security import create_access_token
from app.modules.auth import telegram
from app.modules.auth.schemas import (
    AuthConfig,
    DevLogin,
    TelegramWebAppLogin,
    TelegramWidgetLogin,
    TokenResponse,
)
from app.modules.users.models import User
from app.modules.users.service import to_read


def get_config() -> AuthConfig:
    settings = get_settings()
    return AuthConfig(
        telegram_bot_username=settings.telegram_bot_username,
        dev_login_enabled=settings.app_env == "dev",
    )


def _bot_token() -> str:
    token = get_settings().telegram_bot_token
    if not token:
        raise ServiceUnavailable("Вход через Telegram не настроен", "telegram_not_configured")
    return token


def _verified(verify, *args) -> telegram.TelegramIdentity:
    try:
        return verify(
            *args, _bot_token(), time.time(), get_settings().telegram_auth_max_age_seconds
        )
    except telegram.TelegramAuthError as exc:
        raise Unauthorized(str(exc), "telegram_auth_failed") from exc


async def _login(session: AsyncSession, identity: telegram.TelegramIdentity) -> TokenResponse:
    """Находит пользователя по Telegram id или создаёт; из профиля Telegram берётся только имя."""
    user = await session.scalar(select(User).where(User.telegram_id == identity.telegram_id))
    if user is None:
        user = User(telegram_id=identity.telegram_id)
        session.add(user)
    user.first_name = identity.first_name
    await session.commit()
    return TokenResponse(access_token=create_access_token(user.id), user=to_read(user))


async def login_widget(session: AsyncSession, data: TelegramWidgetLogin) -> TokenResponse:
    fields = {k: str(v) for k, v in data.model_dump(exclude_none=True).items()}
    return await _login(session, _verified(telegram.verify_widget, fields))


async def login_webapp(session: AsyncSession, data: TelegramWebAppLogin) -> TokenResponse:
    return await _login(session, _verified(telegram.verify_webapp, data.init_data))


async def login_dev(session: AsyncSession, data: DevLogin) -> TokenResponse:
    if get_settings().app_env != "dev":
        raise NotFound("Не найдено")
    return await _login(session, telegram.TelegramIdentity(data.telegram_id, data.first_name))
