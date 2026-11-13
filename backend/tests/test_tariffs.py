import itertools
from datetime import date
from decimal import Decimal as D

from app.core.region import get_region
from app.modules.receipts import tariffs

TARIFFS = get_region().tariffs

CODES = {
    "maintenance",
    "cold_water",
    "hot_water",
    "hot_water_heat",
    "sewerage",
    "heating",
    "electricity",
    "gas",
    "waste",
    "capital_repair",
    "common_property_resources",
    "intercom",
    "other",
}


def test_tariffs_file_structure():
    data = TARIFFS
    assert set(data["service_notes"]) == CODES
    for entry in data["tariffs"]:
        assert entry["service_code"] in CODES and entry["unit"] and entry["price_unit"]
        for p in entry["periods"]:
            assert date.fromisoformat(p["from"]) <= date.fromisoformat(p["to"])
            assert p["value"] is None or isinstance(p["value"], str)
            assert isinstance(p["verified"], bool) and p["source_url"].startswith("http")
            if not p["verified"]:
                assert p["note"]


def test_periods_do_not_overlap_within_a_service_variant():
    spans = {}
    for entry in TARIFFS["tariffs"]:
        key = (entry["service_code"], entry.get("variant"))
        for p in entry["periods"]:
            spans.setdefault(key, []).append((p["from"], p["to"]))
    for key, items in spans.items():
        items.sort()
        assert all(a[1] < b[0] for a, b in itertools.pairwise(items)), key


def test_reference_tariffs_switch_on_first_of_october():
    sep, oct_ = (
        tariffs.reference_tariffs(TARIFFS, "2026-09"),
        tariffs.reference_tariffs(TARIFFS, "2026-10"),
    )
    assert sep["cold_water"] == [D("46.8724")] and oct_["cold_water"] == [D("53.4360")]
    assert sep["electricity"] == [D("5.81"), D("4.65")] and oct_["electricity"] == [
        D("6.46"),
        D("5.17"),
    ]


def test_waste_tariff_is_converted_to_square_meters():
    assert tariffs.reference_tariffs(TARIFFS, "2026-10")["waste"] == [D("661.48") * D("0.00709")]


def test_entries_without_value_or_document_are_not_references():
    refs = tariffs.reference_tariffs(TARIFFS, "2026-10")
    assert "gas" not in refs and "hot_water" not in refs


def test_unverified_services():
    assert "electricity" not in tariffs.unverified_services(TARIFFS, "2026-10")
    assert {"cold_water", "heating", "waste"} <= tariffs.unverified_services(TARIFFS, "2026-10")


def test_bad_or_out_of_range_period_has_no_tariffs():
    for period in ("", "2026-13", "abcd", "2025-12", "2027-01"):
        assert tariffs.reference_tariffs(TARIFFS, period) == {}
        assert tariffs.unverified_services(TARIFFS, period) == set()


def test_service_note():
    assert "счётчик" in tariffs.service_note(TARIFFS, "cold_water")
    assert tariffs.service_note(TARIFFS, "unknown") == ""
