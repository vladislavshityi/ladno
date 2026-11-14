"""Ограничение частоты в памяти процесса: запросы к LLM по пользователю, входы по IP."""

import time
from collections import defaultdict, deque
from typing import Annotated

from fastapi import Depends, Request

from app.core.config import get_settings
from app.core.deps import CurrentUser
from app.core.errors import TooManyRequests

WINDOW_SECONDS = 60.0
_calls: defaultdict[str, deque[float]] = defaultdict(deque)


_logins: defaultdict[str, deque[float]] = defaultdict(deque)
LOGIN_WINDOW_SECONDS = 3600.0


def reset_rate_limits() -> None:
    _calls.clear()
    _logins.clear()


async def check_llm_rate_limit(user: CurrentUser) -> None:
    now = time.monotonic()
    calls = _calls[str(user.id)]
    while calls and now - calls[0] > WINDOW_SECONDS:
        calls.popleft()
    if len(calls) >= get_settings().llm_requests_per_minute:
        raise TooManyRequests("Слишком много запросов, попробуйте через минуту")
    calls.append(now)


LLMRateLimit = Depends(check_llm_rate_limit)
LLMRateLimitDep = Annotated[None, LLMRateLimit]


async def check_login_rate_limit(request: Request) -> None:
    """Входы и попытки входа с одного IP: защита от массового создания аккаунтов и подбора.

    IP берётся из X-Forwarded-For, который uvicorn подставляет только от доверенного прокси.
    """
    ip = request.client.host if request.client else "unknown"
    now = time.monotonic()
    attempts = _logins[ip]
    while attempts and now - attempts[0] > LOGIN_WINDOW_SECONDS:
        attempts.popleft()
    limit = get_settings().logins_per_ip_per_hour
    if limit and len(attempts) >= limit:
        wait = int(LOGIN_WINDOW_SECONDS - (now - attempts[0])) + 1
        raise TooManyRequests(
            f"Слишком много попыток входа с вашего адреса. Попробуйте через {-(-wait // 60)} мин",
            "login_rate_limited",
            retry_after=wait,
        )
    attempts.append(now)


LoginRateLimit = Depends(check_login_rate_limit)
