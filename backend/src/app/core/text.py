"""Проверки и обрезка текстов. Чистые функции, без IO."""

import re

_NUMBER = re.compile(r"\d+(?:[.,]\d+)?")
_SENTENCE_END = ".!?"


def numbers_in(text: str) -> set[str]:
    return {n.replace(",", ".") for n in _NUMBER.findall(text)}


def numbers_are_supported(text: str, source: str) -> bool:
    """Все числа из text должны встречаться во входных данных (source)."""
    return numbers_in(text) <= numbers_in(source)


def truncate(text: str, limit: int) -> str:
    """Обрезка до limit символов по границе предложения, иначе по границе слова."""
    if len(text) <= limit:
        return text
    head = text[:limit]
    cut = max(head.rfind(c) for c in _SENTENCE_END) + 1
    if cut >= limit // 2:
        return head[:cut].rstrip()
    if text[limit].isspace():
        return head.rstrip()
    space = head.rfind(" ")
    return head[:space].rstrip() if space > 0 else head


def days_phrase(days: int, kind: str) -> str:
    """«1 рабочего дня», «10 календарных дней»: падеж после «в течение» и «не позднее»."""
    single = days % 10 == 1 and days % 100 != 11
    adjective = {"working": ("рабочего", "рабочих"), "calendar": ("календарного", "календарных")}
    word = adjective[kind][0 if single else 1]
    return f"{days} {word} {'дня' if single else 'дней'}"


def plural(count: int, one: str, few: str, many: str) -> str:
    """Форма слова по числу: plural(1, "житель", "жителя", "жителей") -> «житель»."""
    if count % 10 == 1 and count % 100 != 11:
        return one
    if 2 <= count % 10 <= 4 and not 12 <= count % 100 <= 14:
        return few
    return many
