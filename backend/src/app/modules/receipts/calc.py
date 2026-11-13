"""Общие типы и округление для расчётов по квитанциям. Только Decimal, без IO."""

from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal

ZERO = Decimal("0")
CENT = Decimal("0.01")


def money(value: Decimal) -> Decimal:
    """Копейки, округление как в бухгалтерии: 0.005 -> 0.01."""
    return value.quantize(CENT, rounding=ROUND_HALF_UP)


@dataclass(frozen=True)
class LineData:
    service_code: str
    service_name: str
    accrued: Decimal
    recalculation: Decimal = ZERO
    volume: Decimal | None = None
    tariff: Decimal | None = None
    method: str = "unknown"


@dataclass(frozen=True)
class ReceiptData:
    period: str  # YYYY-MM
    total: Decimal
    lines: tuple[LineData, ...]


_METHOD_ORDER = ("norm_increased", "norm", "meter", "unknown")


def merge_by_service(lines: tuple[LineData, ...]) -> dict[str, LineData]:
    """Строки одной услуги (например, две строки «прочее») сливаются в одну.

    Суммы и объём складываются, тариф и название берутся из первой строки;
    способ расчёта — самый «тяжёлый» из встреченных.
    """
    grouped: dict[str, list[LineData]] = {}
    for line in lines:
        grouped.setdefault(line.service_code, []).append(line)
    return {code: _merge(group) for code, group in grouped.items()}


def _merge(group: list[LineData]) -> LineData:
    if len(group) == 1:
        return group[0]
    volumes = [x.volume for x in group]
    return LineData(
        service_code=group[0].service_code,
        service_name=group[0].service_name,
        accrued=sum((x.accrued for x in group), ZERO),
        recalculation=sum((x.recalculation for x in group), ZERO),
        volume=None if None in volumes else sum(volumes, ZERO),
        tariff=next((x.tariff for x in group if x.tariff is not None), None),
        method=min((x.method for x in group), key=_METHOD_ORDER.index),
    )
