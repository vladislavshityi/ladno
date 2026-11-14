"""Суточные и часовые лимиты на пользователя и общий бюджет запросов к модели.

Счётчики лежат в таблице llm_usage: перезапуск сервиса (а на сервере они частые) их не
сбрасывает, а при нескольких воркерах они общие. Окно считается по UTC.
"""

import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta

from sqlalchemy import DateTime, Integer, String, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column

from app.core.config import get_settings
from app.core.db import Base, utcnow
from app.core.errors import TooManyRequests

GLOBAL = "global"
BUDGET_KIND = "budget"


class LlmUsage(Base):
    """Сколько запросов сделано в окне: subject — id пользователя или «global»."""

    __tablename__ = "llm_usage"

    window: Mapped[datetime] = mapped_column(DateTime(timezone=True), primary_key=True)
    kind: Mapped[str] = mapped_column(String(24), primary_key=True)
    subject: Mapped[str] = mapped_column(String(36), primary_key=True)
    requests: Mapped[int] = mapped_column(Integer, default=0)


@dataclass(frozen=True)
class Rule:
    setting: str  # имя настройки с лимитом
    what: str  # что ограничено, для текста ошибки
    hourly: bool = False


RULES = {
    "classify": Rule("llm_classify_per_hour", "определений категории", hourly=True),
    "receipt_scan": Rule("llm_receipt_scans_per_day", "разборов фото квитанции"),
    "receipt_text": Rule("llm_receipt_texts_per_day", "квитанций и пояснений к ним"),
    "assistant": Rule("llm_assistant_per_day", "сообщений ассистенту"),
    "issue": Rule("issues_per_day", "новых обращений"),
    "photo": Rule("photos_per_day", "загруженных фото"),
}


def _window_start(now: datetime, hourly: bool) -> datetime:
    unit = {"minute": 0, "second": 0, "microsecond": 0}
    return now.replace(**unit) if hourly else now.replace(hour=0, **unit)


def _duration(seconds: int) -> str:
    minutes = max(1, -(-seconds // 60))
    hours, minutes = divmod(minutes, 60)
    if hours:
        return f"{hours} ч {minutes} мин" if minutes else f"{hours} ч"
    return f"{minutes} мин"


async def _bump(
    session: AsyncSession, window: datetime, kind: str, subject: str, limit: int
) -> bool:
    """Прибавляет единицу; False, если лимит окна уже выбран (тогда счётчик не растёт)."""
    stmt = insert(LlmUsage).values(window=window, kind=kind, subject=subject, requests=1)
    stmt = stmt.on_conflict_do_update(
        index_elements=[LlmUsage.window, LlmUsage.kind, LlmUsage.subject],
        set_={"requests": LlmUsage.requests + 1},
        where=LlmUsage.requests < limit if limit else None,
    ).returning(LlmUsage.requests)
    return (await session.execute(stmt)).scalar_one_or_none() is not None


async def consume(session: AsyncSession, user_id: uuid.UUID, kind: str) -> None:
    """Учитывает запрос пользователя; при исчерпании лимита отвечает 429 со временем сброса."""
    rule, settings = RULES[kind], get_settings()
    limit = getattr(settings, rule.setting)
    now = utcnow()
    window = _window_start(now, rule.hourly)
    if not await _bump(session, window, kind, str(user_id), limit):
        end = window + timedelta(hours=1 if rule.hourly else 24)
        seconds = int((end - now).total_seconds())
        period = "час" if rule.hourly else "сутки"
        raise TooManyRequests(
            f"Лимит исчерпан: не больше {limit} {rule.what} за {period}. "
            f"Снова можно через {_duration(seconds)}",
            "quota_exceeded",
            retry_after=seconds,
        )
    await session.commit()


async def budget_used(session: AsyncSession) -> int:
    window = _window_start(utcnow(), False)
    stmt = select(LlmUsage.requests).where(
        LlmUsage.window == window, LlmUsage.kind == BUDGET_KIND, LlmUsage.subject == GLOBAL
    )
    return await session.scalar(stmt) or 0


async def budget_exhausted(session: AsyncSession) -> bool:
    budget = get_settings().llm_daily_request_budget
    return bool(budget) and await budget_used(session) >= budget


async def grant_llm[T](session: AsyncSession, llm: T | None) -> T | None:
    """Модель на один запрос, пока есть общий суточный бюджет; потом None: работают шаблоны.

    Вызывается там, где запрос действительно пойдёт в модель (после кэша и проверок), и сразу
    учитывает его. Запрос может сделать несколько обращений к модели — бюджет считает запросы.
    """
    if llm is None:
        return None
    budget = get_settings().llm_daily_request_budget
    granted = await _bump(session, _window_start(utcnow(), False), BUDGET_KIND, GLOBAL, budget)
    await session.commit()
    return llm if granted else None


async def llm_if_budget_left[T](session: AsyncSession, llm: T | None) -> T | None:
    """Как grant_llm, но ничего не учитывает: для мелких запросов (одна строка квитанции)."""
    return None if llm is None or await budget_exhausted(session) else llm
