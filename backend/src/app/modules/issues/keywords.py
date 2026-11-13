"""Категория по ключевым словам: запасной путь, когда модели нет или она не помогла."""

import re
from collections.abc import Mapping, Sequence
from functools import lru_cache


def normalize(text: str) -> str:
    """Нижний регистр, ё как е, знаки препинания как пробелы."""
    return " ".join(re.sub(r"[^\w]+", " ", text.lower().replace("ё", "е")).split())


@lru_cache
def _pattern(keyword: str) -> tuple[re.Pattern[str], int]:
    """Слова ключа идут подряд, у каждого слова допустимо любое окончание; вес — число слов."""
    words = normalize(keyword).split()
    return re.compile(r"(?<!\w)" + r"\w*\s+".join(map(re.escape, words))), len(words)


def match_category(text: str, keywords: Mapping[str, Sequence[str]]) -> str | None:
    """Категория с наибольшим весом совпавших ключей; при ничьей или без совпадений — None.

    Ключ — корни слов («залив», «не горит свет»): чем длиннее фраза, тем она конкретнее
    и тем больше весит, поэтому «в подъезде нет света» перевешивает общее «нет света».
    """
    normalized = normalize(text)
    scores: dict[str, int] = {}
    for category, roots in keywords.items():
        score = 0
        for root in roots:
            pattern, weight = _pattern(root)
            if pattern.search(normalized):
                score += weight
        if score:
            scores[category] = score
    ranked = sorted(scores.items(), key=lambda item: item[1], reverse=True)
    if not ranked or (len(ranked) > 1 and ranked[0][1] == ranked[1][1]):
        return None
    return ranked[0][0]
