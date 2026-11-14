"""Сколько токенов израсходовано за сутки: только статистика для /api/meta.

Счётчик в памяти процесса и обнуляется при перезапуске; лимитами и бюджетом он не управляет.
"""

from datetime import UTC, datetime

_day: str = ""
_total: int = 0


def _today() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%d")


def add_tokens(count: int) -> None:
    global _day, _total
    if _day != _today():
        _day, _total = _today(), 0
    _total += max(count, 0)


def tokens_today() -> int:
    return _total if _day == _today() else 0


def reset_tokens() -> None:
    global _day, _total
    _day, _total = "", 0
