import pytest

from app.core.text import days_phrase, numbers_are_supported, truncate


def test_numbers_are_supported():
    assert numbers_are_supported("подъезд 2, этаж 3", "подъезд 2, этаж 3-5")
    assert not numbers_are_supported("с 28.10 не горит", "подъезд 2")
    assert numbers_are_supported("2,5 м", "глубина 2.5 м")
    assert numbers_are_supported("без чисел", "")


def test_truncate_short_text_unchanged():
    assert truncate("Коротко.", 100) == "Коротко."


def test_truncate_by_sentence():
    text = "Первое предложение здесь. Второе предложение длиннее."
    assert truncate(text, 40) == "Первое предложение здесь."


def test_truncate_by_word_when_no_sentence():
    assert truncate("слово " * 20, 17) == "слово слово слово"


def test_truncate_hard_cut_single_word():
    assert truncate("а" * 50, 10) == "а" * 10


@pytest.mark.parametrize(
    ("days", "kind", "expected"),
    [
        (1, "calendar", "1 календарного дня"),
        (3, "working", "3 рабочих дней"),
        (10, "working", "10 рабочих дней"),
        (11, "calendar", "11 календарных дней"),
        (21, "working", "21 рабочего дня"),
    ],
)
def test_days_phrase(days: int, kind: str, expected: str):
    assert days_phrase(days, kind) == expected
