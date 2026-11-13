from decimal import Decimal as D

from app.modules.receipts.calc import LineData, ReceiptData
from app.modules.receipts.overcharge import (
    accrual_mismatch,
    find_overcharges,
    sum_mismatch,
    total_overpayment,
)


def line(code="hot_water", accrued="100.00", volume=None, tariff=None, method="meter", recalc="0"):
    return LineData(
        service_code=code,
        service_name=code,
        accrued=D(accrued),
        recalculation=D(recalc),
        volume=D(volume) if volume else None,
        tariff=D(tariff) if tariff else None,
        method=method,
    )


def receipt(*lines, total=None, period="2026-11"):
    total = D(total) if total else sum((x.accrued + x.recalculation for x in lines), D("0"))
    return ReceiptData(period=period, total=total, lines=lines)


def kinds(findings):
    return [(f.type, f.service_code, f.confidence) for f in findings]


def test_accrual_mismatch_tolerance():
    assert not accrual_mismatch(line(volume="10", tariff="50", accrued="500.00"))
    assert not accrual_mismatch(line(volume="10", tariff="50", accrued="510.00"))  # ровно 2%
    assert accrual_mismatch(line(volume="10", tariff="50", accrued="510.01"))
    assert accrual_mismatch(line(volume="10", tariff="50", accrued="489.00"))


def test_accrual_mismatch_skips_lines_without_volume_or_tariff():
    assert not accrual_mismatch(line(accrued="999.00"))
    assert not accrual_mismatch(line(volume="10", accrued="999.00"))
    assert not accrual_mismatch(line(tariff="10", accrued="999.00"))


def test_sum_mismatch_counts_recalculation():
    r = receipt(line(accrued="100.00", recalc="-10.00"), line("sewerage", "50.00"), total="140.00")
    assert not sum_mismatch(r)
    assert not sum_mismatch(receipt(line(accrued="100.00"), total="100.99"))  # в пределах рубля
    assert not sum_mismatch(receipt(line(accrued="100.00"), total="101.00"))  # ровно рубль
    assert sum_mismatch(receipt(line(accrued="100.00"), total="101.01"))


def test_tariff_mismatch_amount_and_tolerance():
    refs = {"cold_water": [D("50.00")]}
    r = receipt(line("cold_water", volume="10", tariff="55.00", accrued="550.00"))
    f = find_overcharges(r, refs)
    assert kinds(f) == [("tariff_mismatch", "cold_water", "high")]
    assert f[0].possible_overpayment == D("50.00")  # (55 - 50) * 10
    ok = receipt(line("cold_water", volume="10", tariff="50.50", accrued="505.00"))  # ровно 1%
    assert find_overcharges(ok, refs) == []
    assert (
        len(
            find_overcharges(
                receipt(line("cold_water", volume="10", tariff="50.51", accrued="505.10")), refs
            )
        )
        == 1
    )


def test_tariff_below_reference_is_not_a_finding():
    refs = {"cold_water": [D("50.00")]}
    assert (
        find_overcharges(
            receipt(line("cold_water", volume="10", tariff="40", accrued="400.00")), refs
        )
        == []
    )


def test_tariff_mismatch_uses_highest_variant():
    refs = {"electricity": [D("5.81"), D("4.65")]}
    gas = receipt(line("electricity", volume="100", tariff="5.81", accrued="581.00"))
    assert find_overcharges(gas, refs) == []
    high = receipt(line("electricity", volume="100", tariff="6.81", accrued="681.00"))
    assert find_overcharges(high, refs)[0].possible_overpayment == D("100.00")


def test_tariff_mismatch_skipped_without_data():
    refs = {"cold_water": [D("50")]}
    assert (
        find_overcharges(receipt(line("cold_water", tariff="70", accrued="10")), refs) == []
    )  # нет объёма
    assert (
        find_overcharges(receipt(line("cold_water", volume="1", accrued="10")), refs) == []
    )  # нет тарифа
    assert (
        find_overcharges(receipt(line("cold_water", volume="1", tariff="70", accrued="70")), {})
        == []
    )
    assert (
        find_overcharges(
            receipt(line("cold_water", volume="1", tariff="70", accrued="70")), {"cold_water": []}
        )
        == []
    )


def test_norm_increased_amount():
    f = find_overcharges(receipt(line(accrued="326.27", method="norm_increased")), {})
    assert kinds(f) == [("norm_increased", "hot_water", "medium")]
    assert f[0].possible_overpayment == D("108.76")  # 326.27 - 326.27 / 1.5


def test_norm_instead_of_meter_estimates_from_previous_volume():
    before = receipt(
        line(volume="4", tariff="60", accrued="240.00", method="meter"), period="2026-10"
    )
    now = receipt(line(volume="6", tariff="60", accrued="360.00", method="norm"))
    f = find_overcharges(now, {}, before)
    assert kinds(f) == [("norm_instead_of_meter", "hot_water", "medium")]
    assert f[0].possible_overpayment == D("120.00")  # 360 - 4 * 60


def test_norm_instead_of_meter_never_negative():
    before = receipt(line(volume="9", tariff="60", accrued="540.00"), period="2026-10")
    now = receipt(line(volume="6", tariff="60", accrued="360.00", method="norm"))
    assert find_overcharges(now, {}, before)[0].possible_overpayment == D("0.00")


def test_norm_instead_of_meter_without_numbers_is_low_confidence():
    before = receipt(line(accrued="100.00", method="meter"), period="2026-10")
    now = receipt(line(accrued="200.00", method="norm"))
    f = find_overcharges(now, {}, before)
    assert kinds(f) == [("norm_instead_of_meter", "hot_water", "low")]
    assert f[0].possible_overpayment == D("0")


def test_norm_after_norm_or_without_history_is_fine():
    now = receipt(line(accrued="200.00", method="norm"))
    assert find_overcharges(now, {}) == []
    before_norm = receipt(line(accrued="100.00", method="norm"), period="2026-10")
    assert find_overcharges(now, {}, before_norm) == []
    other_service = receipt(line("sewerage", accrued="100.00", method="meter"), period="2026-10")
    assert find_overcharges(now, {}, other_service) == []


def test_duplicate_lines():
    a = line("other", volume="1", tariff="10", accrued="10.00")
    f = find_overcharges(receipt(a, a, a), {})
    assert kinds(f) == [("duplicate_line", "other", "medium")] * 2
    assert f[0].possible_overpayment == D("10.00")
    different = line("other", volume="2", tariff="5", accrued="10.00")
    assert find_overcharges(receipt(a, different), {}) == []
    zero = line("other", accrued="0.00")
    assert find_overcharges(receipt(zero, zero), {}) == []


def test_recalculation_findings_only_for_positive():
    f = find_overcharges(receipt(line(recalc="25.00")), {})
    assert kinds(f) == [("unexplained_recalculation", "hot_water", "low")]
    assert f[0].possible_overpayment == D("25.00")
    assert find_overcharges(receipt(line(recalc="-25.00")), {}) == []


def test_clean_receipt_and_total():
    assert (
        find_overcharges(
            receipt(line(volume="1", tariff="100", accrued="100.00")), {"hot_water": [D("100")]}
        )
        == []
    )
    assert find_overcharges(receipt(), {}) == []
    assert total_overpayment([]) == D("0")
    f = find_overcharges(
        receipt(line(accrued="326.27", method="norm_increased", recalc="10.00")), {}
    )
    assert total_overpayment(f) == D("118.76")
