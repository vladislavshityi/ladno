"""Маршрутизация обращений по правилам региона. Чистые функции без IO.

Правила категории: {"questions": [...], "routes": [{"when": {...}, "addressee": ..., ...}],
"default": {...}}. Адресат, нормы и сроки берутся только отсюда, не из LLM.
"""

from dataclasses import dataclass, field
from typing import Any

MANAGING_COMPANY = "managing_company"
HOUSING_INSPECTION = "housing_inspection"


class RulesError(ValueError):
    pass


@dataclass(frozen=True)
class RouteDecision:
    addressee_key: str
    explanation: str = ""
    basis: list[dict[str, Any]] = field(default_factory=list)
    response_deadline: dict[str, Any] | None = None
    fix_deadline: dict[str, Any] | None = None
    escalation: list[str] = field(default_factory=list)
    matched: str = "default"  # "route:<индекс>" или "default"
    shifted: bool = False  # адресат сдвинут из-за already_contacted_uk


def _matches(when: dict[str, Any], answers: dict[str, str]) -> bool:
    for key, expected in when.items():
        allowed = expected if isinstance(expected, list) else [expected]
        if answers.get(key) not in [str(v) for v in allowed]:
            return False
    return True


def select_route(category_rules: dict[str, Any], answers: dict[str, str]) -> tuple[dict, str]:
    """Первое правило, у которого совпали ВСЕ условия `when`; иначе `default`."""
    for i, route in enumerate(category_rules.get("routes") or []):
        if _matches(route.get("when") or {}, answers):
            return route, f"route:{i}"
    default = category_rules.get("default")
    if not default:
        raise RulesError("У категории нет default")
    return default, "default"


def decide(
    category_rules: dict[str, Any], answers: dict[str, str], already_contacted_uk: bool = False
) -> RouteDecision:
    """Выбирает правило и применяет already_contacted_uk.

    Если адресат — УК и житель уже обращался в УК, адресатом становится первая ступень
    эскалации, а лестница сдвигается. Для других адресатов флаг ничего не меняет.
    """
    rule, matched = select_route(category_rules, answers)
    addressee = rule["addressee"]
    escalation = list(rule.get("escalation") or [])
    shifted = False
    if already_contacted_uk and addressee == MANAGING_COMPANY and escalation:
        addressee, escalation, shifted = escalation[0], escalation[1:], True
    return RouteDecision(
        addressee_key=addressee,
        explanation=rule.get("explanation", ""),
        basis=list(rule.get("basis") or []),
        response_deadline=rule.get("response_deadline"),
        fix_deadline=rule.get("fix_deadline"),
        escalation=escalation,
        matched=matched,
        shifted=shifted,
    )
