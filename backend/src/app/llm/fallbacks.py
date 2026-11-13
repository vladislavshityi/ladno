"""Счётчик случаев, когда вместо ответа модели пришлось взять шаблон или правила кода."""

import logging
from collections import Counter

log = logging.getLogger(__name__)

llm_fallback_total: Counter[str] = Counter()


def record_fallback(place: str, reason: str = "ошибка или таймаут модели") -> None:
    """place — место вызова: classify, summary, receipt_parse, receipt_explain, compare."""
    llm_fallback_total[place] += 1
    log.warning("Запасной путь без модели: %s (%s)", place, reason)
