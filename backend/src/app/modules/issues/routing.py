"""Маршрут обращения: решение по правилам региона плюс данные адресатов."""

from typing import Any

from app.core.config import get_settings
from app.core.errors import NotFound
from app.core.region import get_region
from app.modules.houses.models import ManagementCompany
from app.modules.issues import rules
from app.modules.issues.schemas import (
    Addressee,
    Basis,
    Channel,
    Deadline,
    EscalationStep,
    Question,
    RecalculationHint,
    RouteResult,
)

UK_UNKNOWN_NAME = "Ваша УК (укажите её в профиле)"


def category_rules(category: str) -> dict[str, Any]:
    region = get_region()
    found = region.rules.get(category)
    if found is None or region.category(category) is None:
        raise NotFound(f"Неизвестная категория: {category}")
    return found


def get_questions(category: str) -> list[Question]:
    return [Question.model_validate(q) for q in category_rules(category).get("questions") or []]


def _pos_channel() -> Channel:
    return Channel(type="pos", value=get_settings().pos_url, label="Решаем вместе")


def _company_channels(company: ManagementCompany) -> list[Channel]:
    channels = [Channel(type="phone", value=p, label="Телефон УК") for p in company.phones]
    if company.emergency_phone:
        channels.append(Channel(type="phone", value=company.emergency_phone, label="Аварийная"))
    if company.email:
        channels.append(Channel(type="email", value=company.email, label="Почта УК"))
    if company.site:
        channels.append(Channel(type="url", value=company.site, label="Сайт УК"))
    return channels


def _managing_company(company: ManagementCompany | None) -> Addressee:
    channels = [*_company_channels(company), _pos_channel()] if company else [_pos_channel()]
    name = company.name if company else UK_UNKNOWN_NAME
    return Addressee(
        key=rules.MANAGING_COMPANY, name=name, kind="managing_company", channels=channels
    )


def get_addressee(key: str, company: ManagementCompany | None) -> Addressee:
    if key == rules.MANAGING_COMPANY:
        return _managing_company(company)
    entry = get_region().addressees.get(key)
    if entry is None:
        raise NotFound(f"Адресат не найден в справочнике: {key}")
    channels = [Channel.model_validate(c) for c in entry.get("channels") or []]
    return Addressee(key=key, name=entry["name"], kind=entry["kind"], channels=channels)


def _step(key: str, company: ManagementCompany | None) -> EscalationStep:
    return EscalationStep(key=key, name=get_addressee(key, company).name)


def _deadline(raw: dict[str, Any] | None) -> Deadline | None:
    return Deadline.model_validate(raw) if raw else None


def build_route(
    category: str,
    answers: dict[str, str],
    already_contacted_uk: bool,
    company: ManagementCompany | None,
    recalculation_hint: RecalculationHint | None,
) -> RouteResult:
    decision = rules.decide(category_rules(category), answers, already_contacted_uk)
    is_uk = decision.addressee_key == rules.MANAGING_COMPANY
    return RouteResult(
        addressee=get_addressee(decision.addressee_key, company),
        explanation=decision.explanation,
        basis=[Basis.model_validate(b) for b in decision.basis],
        fix_deadline=_deadline(decision.fix_deadline),
        response_deadline=_deadline(decision.response_deadline),
        escalation=[_step(k, company) for k in decision.escalation],
        recalculation_hint=recalculation_hint if is_uk else None,
    )


def build_escalated_route(
    parent: RouteResult, company: ManagementCompany | None
) -> RouteResult | None:
    """Маршрут на следующую ступень лестницы или None, если ступеней не осталось.

    Основания берутся из исходного маршрута (нарушение то же), срок ответа — из данных адресата.
    """
    if not parent.escalation:
        return None
    next_key, rest = parent.escalation[0].key, parent.escalation[1:]
    entry = get_region().addressees.get(next_key, {})
    return RouteResult(
        addressee=get_addressee(next_key, company),
        explanation=f"Следующая ступень после «{parent.addressee.name}»: проблема не решена.",
        basis=parent.basis,
        response_deadline=_deadline(entry.get("response_deadline")),
        escalation=rest,
    )
