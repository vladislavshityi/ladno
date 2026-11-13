import pytest

from app.core.region import get_region
from app.modules.issues.rules import RulesError, decide, select_route

RULES = get_region().rules
ADDRESSEES = get_region().addressees
CATEGORIES = [c["id"] for c in get_region().categories]


# --- валидация данных ---


def test_every_category_has_default():
    assert set(RULES) == set(CATEGORIES)
    for cat, r in RULES.items():
        assert r.get("default", {}).get("addressee"), cat


def _all_rules(r):
    return [*list(r.get("routes") or []), r["default"]]


def test_addressee_keys_exist_and_deadlines_unverified():
    for cat, r in RULES.items():
        for rule in _all_rules(r):
            assert rule["addressee"] in ADDRESSEES, (cat, rule["addressee"])
            assert rule.get("explanation"), cat
            for k in rule.get("escalation") or []:
                assert k in ADDRESSEES, (cat, k)
            for n in rule.get("basis") or []:
                assert n["verified"] is False
            for d in (rule.get("response_deadline"), rule.get("fix_deadline")):
                if d:
                    assert d["type"] in ("working", "calendar") and d["verified"] is False


def test_when_refers_to_declared_questions():
    for cat, r in RULES.items():
        qs = {q["id"]: {o["value"] for o in q["options"]} for q in r.get("questions") or []}
        for route in r.get("routes") or []:
            for qid, val in route["when"].items():
                assert qid in qs, (cat, qid)
                vals = val if isinstance(val, list) else [val]
                assert set(vals) <= qs[qid], (cat, qid, vals)


def test_addressee_entries():
    kinds = {"managing_company", "city", "region", "federal", "emergency", "pos"}
    for key, a in ADDRESSEES.items():
        assert a["kind"] in kinds and a["name"], key
    assert {"vpes", "primvodokanal", "dgk", "peo"} <= set(ADDRESSEES)


# --- домен ---


def test_select_route_first_match_and_list_values():
    rules = {
        "routes": [
            {"when": {"a": "1", "b": ["x", "y"]}, "addressee": "first"},
            {"when": {"a": "1"}, "addressee": "second"},
        ],
        "default": {"addressee": "d"},
    }
    assert select_route(rules, {"a": "1", "b": "y"}) == (rules["routes"][0], "route:0")
    assert select_route(rules, {"a": "1", "b": "z"})[1] == "route:1"
    assert select_route(rules, {})[1] == "default"
    with pytest.raises(RulesError):
        select_route({"routes": []}, {})


# (категория, ответы, ожидаемый адресат, ожидаемое правило)
CASES = [
    (
        "stairwell_lighting",
        {"scope": "whole_entrance", "duration": "days_few"},
        "managing_company",
        "route:0",
    ),
    (
        "stairwell_lighting",
        {"scope": "whole_entrance", "duration": "week_plus"},
        "managing_company",
        "route:0",
    ),
    (
        "stairwell_lighting",
        {"scope": "one_lamp", "duration": "week_plus"},
        "managing_company",
        "route:1",
    ),
    (
        "stairwell_lighting",
        {"scope": "floor", "duration": "days_few"},
        "managing_company",
        "route:2",
    ),
    ("stairwell_lighting", {}, "managing_company", "default"),
    ("graffiti", {"place": "entrance"}, "managing_company", "route:0"),
    ("graffiti", {"place": "house_facade"}, "managing_company", "route:0"),
    ("graffiti", {"place": "stop"}, "city_admin", "route:1"),
    ("graffiti", {"place": "city_object"}, "city_admin", "route:1"),
    ("graffiti", {}, "pos", "default"),
    ("pothole", {"place": "yard"}, "managing_company", "route:0"),
    ("pothole", {"place": "road"}, "city_roads", "route:1"),
    ("pothole", {"place": "sidewalk"}, "city_roads", "route:1"),
    ("pothole", {"place": "unknown"}, "pos", "default"),
]


@pytest.mark.parametrize("cat,answers,addressee,matched", CASES)
def test_p0_rules(cat, answers, addressee, matched):
    d = decide(RULES[cat], answers)
    assert (d.addressee_key, d.matched, d.shifted) == (addressee, matched, False)
    assert d.response_deadline and d.explanation


@pytest.mark.parametrize("cat,answers,addressee,matched", CASES)
def test_p0_already_contacted_uk(cat, answers, addressee, matched):
    base = decide(RULES[cat], answers)
    d = decide(RULES[cat], answers, already_contacted_uk=True)
    if addressee == "managing_company":
        assert d.shifted
        assert d.addressee_key == base.escalation[0] == "housing_inspection"
        assert d.escalation == base.escalation[1:]
    else:
        assert d == base


def test_pothole_road_escalation():
    d = decide(RULES["pothole"], {"place": "road"})
    assert d.escalation == ["traffic_police", "prosecutor"]
    assert d.response_deadline["days"] == 30 and d.response_deadline["type"] == "calendar"


@pytest.mark.parametrize("cat", CATEGORIES)
def test_all_categories_decide_without_answers(cat):
    assert decide(RULES[cat], {}).addressee_key in ADDRESSEES


def test_utility_outage_by_resource():
    got = {
        r: decide(RULES["utility_outage"], {"resource": r}).addressee_key
        for r in ("electricity", "cold_water", "heating")
    }
    assert got == {"electricity": "vpes", "cold_water": "primvodokanal", "heating": "dgk"}


def _answers_for(when):
    return {k: (v[0] if isinstance(v, list) else v) for k, v in when.items()}


@pytest.mark.parametrize("cat", CATEGORIES)
def test_every_route_of_every_category_is_reachable(cat):
    routes = RULES[cat].get("routes") or []
    for i, route in enumerate(routes):
        decision = decide(RULES[cat], _answers_for(route["when"]))
        matched_index = int(decision.matched.split(":")[1])
        assert matched_index <= i, (cat, i)
        assert decision.addressee_key in ADDRESSEES
        assert decision.basis or cat == "other"


def uk_rules_with_ladder():
    """(категория, ответы, правило) для каждого правила с адресатом УК и лестницей."""
    found = []
    for category, r in RULES.items():
        for index, rule in enumerate([*(r.get("routes") or []), r["default"]]):
            if rule["addressee"] == "managing_company" and rule.get("escalation"):
                answers = _answers_for(rule.get("when") or {})
                found.append(pytest.param(category, answers, rule, id=f"{category}-{index}"))
    return found


@pytest.mark.parametrize(("category", "answers", "rule"), uk_rules_with_ladder())
def test_already_contacted_uk_shifts_to_first_escalation_step(category, answers, rule):
    decision = decide(RULES[category], answers, already_contacted_uk=True)
    assert decision.shifted and decision.addressee_key == rule["escalation"][0]
    assert decision.escalation == rule["escalation"][1:]


def test_already_contacted_uk_does_not_change_other_addressees():
    for r in RULES.values():
        for rule in [*(r.get("routes") or []), r["default"]]:
            if rule["addressee"] != "managing_company":
                answers = _answers_for(rule.get("when") or {})
                assert not decide(r, answers, already_contacted_uk=True).shifted
