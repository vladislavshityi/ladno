from fastapi import APIRouter

from app.core.deps import SessionDep
from app.core.rate_limit import LoginRateLimit
from app.modules.auth import service
from app.modules.auth.schemas import (
    AuthConfig,
    DevLogin,
    TelegramWebAppLogin,
    TelegramWidgetLogin,
    TokenResponse,
)

router = APIRouter(prefix="/auth", tags=["auth"])


@router.get("/config", response_model=AuthConfig)
async def get_config() -> AuthConfig:
    """Что нужно странице входа: имя бота для виджета и доступность dev-входа."""
    return service.get_config()


@router.post("/telegram/widget", response_model=TokenResponse, dependencies=[LoginRateLimit])
async def login_widget(data: TelegramWidgetLogin, session: SessionDep) -> TokenResponse:
    """Вход через Telegram Login Widget на сайте."""
    return await service.login_widget(session, data)


@router.post("/telegram/webapp", response_model=TokenResponse, dependencies=[LoginRateLimit])
async def login_webapp(data: TelegramWebAppLogin, session: SessionDep) -> TokenResponse:
    """Вход из Telegram Mini App по initData."""
    return await service.login_webapp(session, data)


@router.post("/dev", response_model=TokenResponse)
async def login_dev(data: DevLogin, session: SessionDep) -> TokenResponse:
    """Вход без Telegram для локальной разработки и демо; при APP_ENV=prod отвечает 404."""
    return await service.login_dev(session, data)
