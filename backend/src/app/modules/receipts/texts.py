"""Шаблонные тексты по квитанциям: запасной вариант без модели или при плохом ответе.

Все числа берутся из расчётов кода, ничего не придумывается.
"""

from decimal import Decimal

from app.core.templates import render
from app.modules.receipts.schemas import Compare, CompareLine, ReceiptLine

MAX_DIFF_ITEMS = 3

_METHOD_NOTES = {
    "meter": "Объём взят по показаниям счётчика.",
    "norm": "Начислено по нормативу, показания счётчика не учтены.",
    "norm_increased": (
        "Начислено по нормативу с повышающим коэффициентом 1,5: скорее всего, "
        "истёк срок поверки счётчика или не переданы показания."
    ),
}


def _num(value: Decimal) -> str:
    """Число по-русски: запятая, без лишних нулей, но не меньше двух знаков после запятой."""
    whole, _, fraction = format(value, "f").partition(".")
    return f"{whole},{fraction.rstrip('0').ljust(2, '0')}"


def _signed(value: Decimal) -> str:
    return ("+" if value > 0 else "") + _num(value)


def _facts(line: ReceiptLine) -> str:
    text = f"Начислено {_num(line.accrued)} ₽"
    if line.volume is not None and line.tariff is not None:
        volume = f"{_num(line.volume)} {line.unit or ''}".strip()
        text += f": {volume} × {_num(line.tariff)} ₽"
    text += "."
    if line.recalculation:
        text += f" Перерасчёт: {_num(line.recalculation)} ₽."
    return text


def line_explanation(line: ReceiptLine, service_note: str) -> str:
    return render(
        "receipts/line_explanation.j2",
        note=service_note,
        facts=_facts(line),
        method_note=_METHOD_NOTES.get(line.method, ""),
    )


def _reason(line: CompareLine) -> str:
    if "new_line" in line.flags:
        return "строка появилась в квитанции"
    if "removed_line" in line.flags:
        return "строки больше нет"
    by_tariff, by_volume = _signed(line.delta_tariff), _signed(line.delta_volume)
    if abs(line.delta_tariff) >= abs(line.delta_volume) and line.delta_tariff != 0:
        return (
            f"в основном изменился тариф: {by_tariff} ₽ из-за тарифа и {by_volume} ₽ из-за объёма"
        )
    if line.delta_volume != 0:
        return (
            f"в основном изменился объём: {by_volume} ₽ из-за объёма и {by_tariff} ₽ из-за тарифа"
        )
    return "изменение связано с перерасчётом или округлением"


def _notes(diff: Compare) -> list[str]:
    notes = []
    if "heating_season_start" in diff.flags:
        notes.append("Начался отопительный сезон: в квитанции появилась строка отопления.")
    if "tariff_indexation" in diff.flags:
        notes.append("Сработала плановая индексация тарифов.")
    notes += [
        f"По строке «{x.service_name}» начисление идёт по нормативу с повышающим коэффициентом."
        for x in diff.lines
        if "norm_increased" in x.flags
    ]
    return notes


def diff_explanation(diff: Compare) -> str:
    changed = sorted(
        (x for x in diff.lines if x.delta != 0), key=lambda x: abs(x.delta), reverse=True
    )
    items = [
        {"name": x.service_name, "delta": _signed(x.delta), "reason": _reason(x)}
        for x in changed[:MAX_DIFF_ITEMS]
    ]
    return render(
        "receipts/diff_explanation.j2",
        unchanged=diff.total_delta == 0,
        growing=diff.total_delta > 0,
        delta_abs=_num(abs(diff.total_delta)),
        total_base=_num(diff.total_base),
        total_target=_num(diff.total_target),
        items=items,
        notes=_notes(diff),
    )
