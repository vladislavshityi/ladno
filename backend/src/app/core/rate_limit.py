"""Ограничение частоты запросов к LLM: в памяти процесса, по пользователю."""

import time
from collections import defaultdict, deque
from typing import Annotated

from fastapi import Depends

from app.core.config import get_settings
from app.core.deps import CurrentUser
from app.core.errors import TooManyRequests

WINDOW_SECONDS = 60.0
_calls: defaultdict[str, deque[float]] = defaultdict(deque)


def reset_rate_limits() -> None:
    _calls.clear()


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
