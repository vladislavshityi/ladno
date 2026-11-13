"""Сравнение двух квитанций по месяцам: что изменилось и почему. Чистые функции, без IO."""

from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal

from app.modules.receipts.calc import ZERO, LineData, ReceiptData, merge_by_service, money

GROWTH_PCT = Decimal("15")
PCT_STEP = Decimal("0.1")
# месяцы, с которых в 2026 году меняются тарифы (1 января и 1 октября)
INDEXATION_MONTHS = frozenset({1, 10})
NORM_METHODS = frozenset({"norm", "norm_increased"})


@dataclass(frozen=True)
class LineDiff:
    service_code: str
    service_name: str
    accrued_base: Decimal
    accrued_target: Decimal
    delta: Decimal
    delta_pct: Decimal | None
    delta_tariff: Decimal
    delta_volume: Decimal
    delta_other: Decimal
    flags: tuple[str, ...]


@dataclass(frozen=True)
class ReceiptDiff:
    base_period: str
    target_period: str
    total_base: Decimal
    total_target: Decimal
    total_delta: Decimal
    lines: tuple[LineDiff, ...]
    flags: tuple[str, ...]


def _pct(delta: Decimal, base: Decimal) -> Decimal | None:
    if base == ZERO:
        return None
    return (delta / base * 100).quantize(PCT_STEP, rounding=ROUND_HALF_UP)


def _split(base: LineData, target: LineData, delta: Decimal) -> tuple[Decimal, Decimal, Decimal]:
    """Разложение изменения на тариф, объём и остальное (перерасчёты, округления)."""
    if None in (base.tariff, target.tariff, base.volume, target.volume):
        return ZERO, ZERO, delta
    by_tariff = money((target.tariff - base.tariff) * base.volume)
    by_volume = money((target.volume - base.volume) * target.tariff)
    return by_tariff, by_volume, delta - by_tariff - by_volume


def _target_flags(target: LineData) -> tuple[str, ...]:
    flags = []
    if target.method == "norm_increased":
        flags.append("norm_increased")
    if target.recalculation != ZERO:
        flags.append("has_recalculation")
    if "пени" in target.service_name.lower():
        flags.append("has_penalty")
    return tuple(flags)


def _flags(base: LineData | None, target: LineData | None, pct: Decimal | None) -> tuple[str, ...]:
    if base is None:
        return ("new_line", *_target_flags(target))
    if target is None:
        return ("removed_line",)
    flags = []
    if pct is not None and pct > GROWTH_PCT:
        flags.append("growth_over_15pct")
    if base.method == "meter" and target.method in NORM_METHODS:
        flags.append("switched_to_norm")
    if None not in (base.tariff, target.tariff) and base.tariff != target.tariff:
        flags.append("tariff_changed")
    return tuple(flags) + _target_flags(target)


def _line_diff(code: str, base: LineData | None, target: LineData | None) -> LineDiff:
    accrued_base = base.accrued if base else ZERO
    accrued_target = target.accrued if target else ZERO
    delta = accrued_target - accrued_base
    pct = _pct(delta, accrued_base)
    if base and target:
        by_tariff, by_volume, other = _split(base, target, delta)
    else:  # строка появилась или пропала целиком: это «объём», а не тариф
        by_tariff, by_volume, other = ZERO, delta, ZERO
    return LineDiff(
        service_code=code,
        service_name=(target or base).service_name,
        accrued_base=accrued_base,
        accrued_target=accrued_target,
        delta=delta,
        delta_pct=pct,
        delta_tariff=by_tariff,
        delta_volume=by_volume,
        delta_other=other,
        flags=_flags(base, target, pct),
    )


def _common_flags(lines: tuple[LineDiff, ...], target_period: str) -> tuple[str, ...]:
    flags = []
    if any(x.service_code == "heating" and "new_line" in x.flags for x in lines):
        flags.append("heating_season_start")
    month = int(target_period[5:7])
    if month in INDEXATION_MONTHS and any("tariff_changed" in x.flags for x in lines):
        flags.append("tariff_indexation")
    return tuple(flags)


def compare(base: ReceiptData, target: ReceiptData) -> ReceiptDiff:
    base_lines = merge_by_service(base.lines)
    target_lines = merge_by_service(target.lines)
    codes = list(target_lines) + [c for c in base_lines if c not in target_lines]
    lines = tuple(_line_diff(c, base_lines.get(c), target_lines.get(c)) for c in codes)
    return ReceiptDiff(
        base_period=base.period,
        target_period=target.period,
        total_base=base.total,
        total_target=target.total,
        total_delta=target.total - base.total,
        lines=lines,
        flags=_common_flags(lines, target.period),
    )
