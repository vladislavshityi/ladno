import pytest

from app.core.region import get_region
from app.modules.issues.keywords import match_category, normalize

PHRASES = {
    "stairwell_lighting": ["В подъезде не горит свет", "Перегорела лампочка на лестнице"],
    "graffiti": ["На стене дома граффити", "Исписали стену подъезда баллончиком"],
    "pothole": ["Во дворе большая яма", "Выбоина на асфальте у дома"],
    "stairwell_cleaning": ["В подъезде грязно, не моют лестницу", "Давно не было уборки подъезда"],
    "elevator": ["Не работает лифт", "Застряли в лифте"],
    "entrance_door": ["Сломался домофон", "Дверь в подъезд не закрывается"],
    "flooding": ["Нас затопили соседи сверху", "Прорвало трубу, вода течёт с потолка"],
    "roof_leak": ["Протекает крыша", "С кровли течёт на чердаке после дождя"],
    "garbage": ["Переполнены мусорные баки", "Мусор не вывозят неделю"],
    "snow_ice": ["Во дворе не чистят снег", "Гололёд и сосульки у подъезда"],
    "open_manhole": ["Открытый люк на тротуаре", "Нет крышки колодца"],
    "utility_outage": ["Нет горячей воды", "Отключили отопление, холодные батареи"],
}


def keywords() -> dict[str, list[str]]:
    return {c["id"]: c.get("keywords", []) for c in get_region().categories}


def test_every_category_has_keywords_except_other():
    found = keywords()
    assert len(found) == 13 and found["other"] == []
    assert all(found[category] for category in PHRASES)


@pytest.mark.parametrize(
    ("category", "text"), [(c, t) for c, texts in PHRASES.items() for t in texts]
)
def test_phrase_is_matched_to_category(category: str, text: str):
    assert match_category(text, keywords()) == category


def test_no_match_means_no_category():
    assert match_category("что-то не так", keywords()) is None
    assert match_category("", keywords()) is None


def test_tie_means_no_category():
    assert match_category("лифт и домофон", keywords()) is None


def test_longer_phrase_outweighs_generic_one():
    assert match_category("в подъезде нет света", keywords()) == "stairwell_lighting"
    assert match_category("в квартире нет света", keywords()) == "utility_outage"


def test_yo_case_and_punctuation_are_normalized():
    assert normalize("  ТЕЧЁТ,  крыша!! ") == "течет крыша"
    assert match_category("ПРОТЕКАЕТ КРЫША!", keywords()) == "roof_leak"


def test_roots_match_only_word_beginnings():
    assert match_category("капитальный ремонт", {"x": ["кап"]}) == "x"
    assert match_category("рекапитализация", {"x": ["кап"]}) is None
