"""Проверка начислений по тарифам: где квитанция может быть завышена. Чистые функции, без IO.

Формулировки результата вероятностные: код только находит расхождения и считает сумму,
решает пользователь.
"""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from decimal import Decimal

from app.modules.receipts.calc import ZERO, LineData, ReceiptData, money

TARIFF_TOLERANCE = Decimal("0.01")  # 1%: допуск между тарифом в строке и справочником
ACCRUAL_TOLERANCE = Decimal("0.02")  # 2%: допуск между «объём × тариф» и начислением
SUM_TOLERANCE = Decimal("1")  # ₽: допуск между суммой строк и итогом
NORM_FACTOR = Decimal("1.5")  # повышающий коэффициент к нормативу


@dataclass(frozen=True)
class FindingData:
    type: str
    service_code: str
    possible_overpayment: Decimal
    confidence: str  # high | medium | low


def accrual_mismatch(line: LineData, tolerance: Decimal = ACCRUAL_TOLERANCE) -> bool:
    """Начислено заметно отличается от объём × тариф. Без объёма или тарифа проверять нечего."""
    if line.volume is None or line.tariff is None:
        return False
    expected = line.volume * line.tariff
    return abs(line.accrued - expected) > expected * tolerance


def sum_mismatch(receipt: ReceiptData, tolerance: Decimal = SUM_TOLERANCE) -> bool:
    """Сумма «к оплате» по строкам не сходится с итогом квитанции."""
    lines_total = sum((x.accrued + x.recalculation for x in receipt.lines), ZERO)
    return abs(lines_total - receipt.total) > tolerance


def _tariff_mismatch(line: LineData, references: Sequence[Decimal]) -> FindingData | None:
    if line.tariff is None or line.volume is None or not references:
        return None
    reference = max(
        references
    )  # вариантов тарифа несколько: берём самый высокий, чтобы не ошибиться в пользу жалобы
    if line.tariff <= reference * (1 + TARIFF_TOLERANCE):
        return None
    amount = money((line.tariff - reference) * line.volume)
    return FindingData("tariff_mismatch", line.service_code, amount, "high")


def _norm_increased(line: LineData) -> FindingData | None:
    if line.method != "norm_increased":
        return None
    amount = money(line.accrued - line.accrued / NORM_FACTOR)
    return FindingData("norm_increased", line.service_code, amount, "medium")


def _norm_instead_of_meter(line: LineData, previous: LineData | None) -> FindingData | None:
    if line.method != "norm" or previous is None or previous.method != "meter":
        return None
    if previous.volume is None or line.tariff is None:
        return FindingData("norm_instead_of_meter", line.service_code, ZERO, "low")
    amount = max(ZERO, money(line.accrued - previous.volume * line.tariff))
    return FindingData("norm_instead_of_meter", line.service_code, amount, "medium")


def _duplicates(lines: tuple[LineData, ...]) -> list[FindingData]:
    seen: set[tuple] = set()
    found = []
    for line in lines:
        key = (line.service_code, line.volume, line.tariff, line.accrued)
        if line.accrued != ZERO and key in seen:
            found.append(FindingData("duplicate_line", line.service_code, line.accrued, "medium"))
        seen.add(key)
    return found


def _recalculation(line: LineData) -> FindingData | None:
    if line.recalculation <= ZERO:
        return None
    return FindingData("unexplained_recalculation", line.service_code, line.recalculation, "low")


def find_overcharges(
    receipt: ReceiptData,
    references: Mapping[str, Sequence[Decimal]],
    previous: ReceiptData | None = None,
) -> list[FindingData]:
    """references: допустимые тарифы на период квитанции по service_code (в единицах строки).

    previous: предыдущая квитанция владельца, нужна для «норматив вместо счётчика».
    """
    before = {x.service_code: x for x in previous.lines} if previous else {}
    found: list[FindingData] = []
    for line in receipt.lines:
        checks = (
            _tariff_mismatch(line, references.get(line.service_code, ())),
            _norm_increased(line),
            _norm_instead_of_meter(line, before.get(line.service_code)),
            _recalculation(line),
        )
        found.extend(f for f in checks if f is not None)
    return found + _duplicates(receipt.lines)


def total_overpayment(findings: Sequence[FindingData]) -> Decimal:
    return sum((f.possible_overpayment for f in findings), ZERO)
