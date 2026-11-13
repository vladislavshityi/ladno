import hmac
from typing import Annotated

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.db import get_session
from app.core.errors import Forbidden, Unauthorized
from app.core.security import decode_access_token
from app.llm.client import LLMClient, get_llm
from app.modules.users.models import User

SessionDep = Annotated[AsyncSession, Depends(get_session)]
LLMDep = Annotated[LLMClient | None, Depends(get_llm)]
_bearer = HTTPBearer(auto_error=False)


async def get_current_user(
    session: SessionDep,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
) -> User:
    if credentials is None:
        raise Unauthorized("Требуется вход", "not_authenticated")
    user = await session.get(User, decode_access_token(credentials.credentials))
    if user is None:
        raise Unauthorized("Пользователь не найден", "invalid_token")
    return user


async def get_consented_user(user: Annotated[User, Depends(get_current_user)]) -> User:
    """Данные сохраняются только после согласия на обработку актуальной версии."""
    if user.consent_version != get_settings().consent_version:
        raise Forbidden("Нужно согласие на обработку персональных данных", "consent_required")
    return user


def require_bot(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
) -> None:
    """Служебные эндпоинты бота: общий секрет BOT_API_TOKEN вместо пользовательского JWT."""
    expected = get_settings().bot_api_token
    if not expected or credentials is None:
        raise Unauthorized("Нужен служебный токен бота", "invalid_bot_token")
    if not hmac.compare_digest(credentials.credentials, expected):
        raise Unauthorized("Нужен служебный токен бота", "invalid_bot_token")


CurrentUser = Annotated[User, Depends(get_current_user)]
ConsentedUser = Annotated[User, Depends(get_consented_user)]
BotAuth = Depends(require_bot)
