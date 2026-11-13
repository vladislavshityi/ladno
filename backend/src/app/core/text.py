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
