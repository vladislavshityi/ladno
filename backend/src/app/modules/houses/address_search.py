"""Поиск адреса среди домов справочника: прощает регистр, пропуски, порядок слов и опечатки."""

import re
from collections.abc import Sequence
from typing import NamedTuple

_STREET_TYPES = {
    "г", "город", "владивосток",
    "ул", "улица", "пр", "кт", "проспект", "пер", "переулок", "б", "р", "бульвар",
    "ш", "шоссе", "наб", "набережная", "пл", "площадь", "проезд", "туп", "тупик",
    "мкр", "микрорайон", "п", "пос", "поселок", "о", "остров",
}  # fmt: skip
_HOUSE_MARKS = {
    "д": "", "дом": "", "к": "к", "корп": "к", "корпус": "к",
    "стр": "с", "строение": "с", "лит": "л", "литера": "л",
}  # fmt: skip
# «2-я», «2й»: порядковое число в названии улицы, а не номер дома
_TOKEN = re.compile(r"\d+-(?:я|й|е|ая|ой|ий|ый|ое)(?![а-я])|\d+(?:я|й)(?![а-я])|\d+|[^\W\d_]+|/")

MIN_TYPO_LEN = 5


class HouseKey(NamedTuple):
    street: tuple[str, ...]
    number: str | None


class Query(NamedTuple):
    words: tuple[str, ...]
    number: str | None


def _tokens(text: str) -> list[str]:
    text = text.lower().replace("ё", "е").replace("пр-кт", "проспект").replace("б-р", "бульвар")
    tokens = []
    for token in _TOKEN.findall(text):
        if token[0].isdigit() and not token.isdigit():
            token = re.sub(r"\D", "", token) + "я"
        tokens.append(token)
    return tokens


def _is_ordinal(token: str) -> bool:
    return token.endswith("я") and token[0].isdigit()


def _is_number_start(token: str) -> bool:
    return token[0].isdigit() and not _is_ordinal(token)


def _street_words(tokens: Sequence[str]) -> tuple[str, ...]:
    skipped = _STREET_TYPES | _HOUSE_MARKS.keys() | {"/"}
    return tuple(t for t in tokens if t not in skipped)


def _house_number(tokens: Sequence[str]) -> str | None:
    """«5 а» -> 5а, «16 / 1» -> 16/1, «12 корп 2» -> 12к2."""
    return "".join(_HOUSE_MARKS.get(t, t) for t in tokens) or None


def _split(tokens: Sequence[str]) -> tuple[list[str], list[str]]:
    for i, token in enumerate(tokens):
        if _is_number_start(token):
            return list(tokens[:i]), list(tokens[i:])
    return list(tokens), []


def parse_query(q: str) -> Query | None:
    """None, если в запросе нет ни одного слова улицы."""
    street, house = _split(_tokens(q))
    words = _street_words(street)
    return Query(words, _house_number(house)) if words else None


def parse_address(address: str) -> HouseKey:
    """«г Владивосток, ул Кутузова, д 5А» -> улица (кутузова,), номер 5а."""
    parts = address.split(", ")
    number = None
    if len(parts) > 1 and parts[-1].startswith("д "):
        number = _house_number(_tokens(parts[-1]))
        parts = parts[:-1]
    return HouseKey(_street_words(_tokens(" ".join(parts[1:]))), number)


def one_edit_apart(a: str, b: str) -> bool:
    """Расстояние Левенштейна не больше 1: одна вставка, удаление или замена."""
    if abs(len(a) - len(b)) > 1:
        return False
    if len(a) > len(b):
        a, b = b, a
    i = 0
    while i < len(a) and a[i] == b[i]:
        i += 1
    if i == len(a):
        return True
    if len(a) == len(b):
        return a[i + 1 :] == b[i + 1 :]
    return a[i:] == b[i + 1 :]


def _word_rank(query_word: str, street_word: str) -> int | None:
    """0 — слово целиком, 1 — начало слова, 2 — опечатка в один символ."""
    if query_word == street_word:
        return 0
    if street_word.startswith(query_word):
        return 1
    if len(query_word) >= MIN_TYPO_LEN and (
        one_edit_apart(query_word, street_word)
        or one_edit_apart(query_word, street_word[: len(query_word)])
    ):
        return 2
    return None


def _street_rank(words: Sequence[str], street: Sequence[str]) -> int | None:
    worst = 0
    for word in words:
        ranks = [r for sw in street if (r := _word_rank(word, sw)) is not None]
        if not ranks:
            return None
        worst = max(worst, min(ranks))
    return worst


def _number_rank(query: str | None, house: str | None) -> int | None:
    """0 — номер совпал точно, 1 — введено начало номера."""
    if query is None:
        return 0
    if house is None:
        return None
    if house == query:
        return 0
    return 1 if house.startswith(query) else None


def search(q: str, items: Sequence[tuple[str, HouseKey]], limit: int) -> list[int]:
    """Индексы подходящих элементов (адрес, ключ) от лучшего к худшему."""
    query = parse_query(q)
    if query is None:
        return []
    street_ranks: dict[tuple[str, ...], int | None] = {}
    found = []
    for idx, (address, key) in enumerate(items):
        if key.street not in street_ranks:
            street_ranks[key.street] = _street_rank(query.words, key.street)
        street_rank = street_ranks[key.street]
        number_rank = _number_rank(query.number, key.number)
        if street_rank is not None and number_rank is not None:
            found.append(((street_rank, number_rank, len(address), address), idx))
    found.sort()
    return [idx for _, idx in found[:limit]]
