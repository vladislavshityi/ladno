"""Небольшой кэш в памяти с временем жизни: хранит значения по хэшам, а не по тексту жителя."""

import hashlib
import re
import time
from typing import Any


def text_key(text: str) -> str:
    """Хэш текста без регистра и лишних пробелов: «Лифт  сломан» и «лифт сломан» совпадают."""
    normalized = re.sub(r"\s+", " ", text.strip().lower())
    return hashlib.sha256(normalized.encode()).hexdigest()


class TtlCache:
    def __init__(self, ttl_seconds: float, max_size: int) -> None:
        self._ttl, self._max_size = ttl_seconds, max_size
        self._items: dict[str, tuple[float, Any]] = {}

    def get(self, key: str) -> Any | None:
        hit = self._items.get(key)
        if hit is None or time.monotonic() - hit[0] > self._ttl:
            self._items.pop(key, None)
            return None
        return hit[1]

    def set(self, key: str, value: Any) -> None:
        if len(self._items) >= self._max_size:
            self._items.pop(next(iter(self._items)))  # самая старая запись
        self._items[key] = (time.monotonic(), value)

    def clear(self) -> None:
        self._items.clear()
