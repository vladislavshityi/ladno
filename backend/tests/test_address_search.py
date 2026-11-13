"""Поиск адреса: нормализация, разбор запроса и ранжирование."""

import pytest

from app.modules.houses.address_search import (
    HouseKey,
    one_edit_apart,
    parse_address,
    parse_query,
    search,
)


def _items(addresses):
    return [(a, parse_address(a)) for a in addresses]


def _found(q, addresses, limit=10):
    items = _items(addresses)
    return [items[i][0] for i in search(q, items, limit)]


@pytest.mark.parametrize(
    "q",
    [
        "Кутузова 5а",
        "кутузова, 5 а",
        "ул. Кутузова д.5А",
        "улица КУТУЗОВА дом 5-а",
        "г Владивосток Кутузова 5А",
    ],
)
def test_query_variants_give_same_house(q):
    assert parse_query(q) == parse_query("кутузова 5а")
    assert parse_query(q).number == "5а"


def test_parse_address():
    assert parse_address("г Владивосток, ул Кутузова, д 5А") == HouseKey(("кутузова",), "5а")
    assert parse_address("г Владивосток, ул 2-я Поселковая, д 22 корп 2") == HouseKey(
        ("2я", "поселковая"), "22к2"
    )
    assert parse_address("г Владивосток, пр-кт Красного Знамени, д 45").street == (
        "красного",
        "знамени",
    )
    assert parse_address("г Владивосток, ул Расула Гамзатова, д 5 корп 2/3").number == "5к2/3"
    assert parse_address("г Владивосток, п Трудовое, д 31") == HouseKey(("трудовое",), "31")
    assert parse_address("г Владивосток, ул Ёлочная") == HouseKey(("елочная",), None)


@pytest.mark.parametrize(
    "raw,number",
    [
        ("Маковского 16/1", "16/1"),
        ("Маковского 12 к2", "12к2"),
        ("Маковского 12к2", "12к2"),
        ("Маковского 12 корп 2", "12к2"),
        ("Маковского 12 корпус 2", "12к2"),
        ("Маковского 3 стр 1", "3с1"),
        ("Маковского 5 а", "5а"),
        ("Маковского 5", "5"),
        ("Маковского", None),
    ],
)
def test_house_number_canonical(raw, number):
    assert parse_query(raw).number == number


def test_ordinal_is_street_word_not_number():
    assert parse_query("2-я Поселковая").words == ("2я", "поселковая")
    assert parse_query("поселковая 2я").words == ("поселковая", "2я")
    assert parse_query("2-я Поселковая 3").number == "3"


@pytest.mark.parametrize("q", ["", "   ", "!!!", "5", "ул", "г Владивосток", "д 5", "?!. ,"])
def test_meaningless_query(q):
    assert parse_query(q) is None
    assert search(q, _items(["г Владивосток, ул Кутузова, д 5"]), 10) == []


def test_exact_number_before_prefix():
    addrs = [
        "г Владивосток, ул Кутузова, д 50",
        "г Владивосток, ул Кутузова, д 5Б",
        "г Владивосток, ул Кутузова, д 5",
        "г Владивосток, ул Кутузова, д 5А",
        "г Владивосток, ул Кутузова, д 7",
    ]
    res = _found("Кутузова 5", addrs)
    assert res[0].endswith("д 5")
    assert set(res) == set(addrs[:4])
    assert _found("Кутузова 5а", addrs) == ["г Владивосток, ул Кутузова, д 5А"]


def test_no_number_in_query_matches_all_houses_of_street():
    addrs = [
        "г Владивосток, ул Кутузова, д 7",
        "г Владивосток, ул Кутузова, д 5",
        "г Владивосток, ул Русская, д 1",
    ]
    assert _found("кутуз", addrs) == [addrs[1], addrs[0]]


def test_house_without_number_not_found_by_number():
    assert _found("Ёлочная 5", ["г Владивосток, ул Ёлочная"]) == []


def test_word_order_and_ordinals():
    addrs = ["г Владивосток, ул 2-я Поселковая, д 3", "г Владивосток, ул 3-я Поселковая, д 3"]
    assert _found("2-я Поселковая", addrs) == [addrs[0]]
    assert _found("Поселковая 2-я 3", addrs) == [addrs[0]]
    assert _found("поселковая 2я", addrs) == [addrs[0]]


def test_all_words_must_match():
    addrs = ["г Владивосток, ул Расула Гамзатова, д 5", "г Владивосток, ул Расула Ахметова, д 5"]
    assert _found("Расула Гамзатова", addrs) == [addrs[0]]
    assert _found("Гамзатова Ахметова", addrs) == []


def test_corpus_and_fraction():
    addrs = [
        "г Владивосток, ул Маковского, д 12 корп 2",
        "г Владивосток, ул Маковского, д 16/1",
        "г Владивосток, ул Маковского, д 12",
    ]
    assert _found("Маковского 12 к2", addrs) == [addrs[0]]
    assert _found("маковского 16/1", addrs) == [addrs[1]]
    assert _found("маковского 12", addrs) == [addrs[2], addrs[0]]


def test_street_type_variants_ignored():
    addrs = [
        "г Владивосток, пр-кт Красного Знамени, д 45",
        "г Владивосток, б-р Приморский, д 1",
        "г Владивосток, пер Днепровский, д 5",
    ]
    assert _found("проспект красного знамени 45", addrs) == [addrs[0]]
    assert _found("пр-кт Красного знамени 45", addrs) == [addrs[0]]
    assert _found("бульвар Приморский 1", addrs) == [addrs[1]]
    assert _found("Днепровский переулок 5", addrs) == [addrs[2]]


def test_typo_ranks_below_exact_and_prefix():
    assert _found(
        "Светланкая 10", ["г Владивосток, ул Светланская, д 10", "г Владивосток, ул Русская, д 10"]
    ) == ["г Владивосток, ул Светланская, д 10"]
    typo_first = ["г Владивосток, ул Светланскя, д 10", "г Владивосток, ул Светланская, д 10"]
    assert _found("светланская 10", typo_first) == typo_first[::-1]
    prefix_and_typo = [
        "г Владивосток, ул Светланкая, д 10",
        "г Владивосток, ул Светлановская, д 10",
    ]
    assert _found("светлановск 10", prefix_and_typo)[0] == prefix_and_typo[1]


def test_short_words_do_not_get_typo_tolerance():
    assert _found("Русска 5", ["г Владивосток, ул Русская, д 5"]) != []
    assert _found("Мара 5", ["г Владивосток, ул Мира, д 5"]) == []


def test_ranking_prefers_exact_word_then_shorter_then_alphabet():
    addrs = ["г Владивосток, ул Светланская, д 10", "г Владивосток, ул Светлановская, д 10"]
    assert _found("светлановская", addrs) == [addrs[1]]
    assert _found("светлан", addrs) == addrs
    assert _found("светлан", addrs[::-1]) == addrs


def test_limit():
    addrs = [f"г Владивосток, ул Кутузова, д {n}" for n in range(1, 30)]
    assert len(_found("Кутузова", addrs, limit=10)) == 10


@pytest.mark.parametrize(
    "a,b,expected",
    [
        ("abcde", "abcde", True),
        ("abcde", "abxde", True),
        ("abcde", "abcd", True),
        ("abcde", "abcdef", True),
        ("abcde", "bcde", True),
        ("abcde", "abxyz", False),
        ("abcde", "abc", False),
        ("abcde", "bacde", False),
    ],
)
def test_one_edit_apart(a, b, expected):
    assert one_edit_apart(a, b) is expected
