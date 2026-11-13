"""Сроки обращений. Чистые функции без IO."""

from datetime import datetime, timedelta

from app.modules.issues.models import ACTIVE_STATUSES, IssueStatus


def add_deadline(start: datetime, days: int, kind: str) -> datetime:
    """calendar: +N суток; working: +N рабочих дней (сб и вс пропускаются, праздники нет)."""
    if days < 0:
        raise ValueError("days must be >= 0")
    if kind == "calendar":
        return start + timedelta(days=days)
    if kind == "working":
        current, left = start, days
        while left > 0:
            current += timedelta(days=1)
            if current.weekday() < 5:
                left -= 1
        return current
    raise ValueError(f"unknown deadline type: {kind!r}")


def is_overdue(now: datetime, deadline_at: datetime | None, status: IssueStatus) -> bool:
    """Срок ответа истёк у поданного обращения, которое ещё не закрыто."""
    return deadline_at is not None and status in ACTIVE_STATUSES and now > deadline_at
