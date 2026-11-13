from decimal import Decimal as D

from app.modules.receipts.calc import LineData, ReceiptData, merge_by_service, money
from app.modules.receipts.diff import compare


def line(
    code="cold_water",
    accrued="100.00",
    volume=None,
    tariff=None,
    method="meter",
    recalc="0",
    name=None,
):
    return LineData(
        service_code=code,
        service_name=name or code,
        accrued=D(accrued),
        recalculation=D(recalc),
        volume=D(volume) if volume else None,
        tariff=D(tariff) if tariff else None,
        method=method,
    )


def receipt(period, *lines):
    return ReceiptData(
        period=period, total=sum((x.accrued + x.recalculation for x in lines), D("0")), lines=lines
    )


def one(base, target, period="2026-11"):
    diff = compare(receipt("2026-10", base), receipt(period, target))
    return diff, diff.lines[0]


def test_money_rounds_half_up():
    assert money(D("0.005")) == D("0.01")
    assert money(D("2.675")) == D("2.68")
    assert money(D("1.004")) == D("1.00")
    assert money(D("-0.005")) == D("-0.01")


def test_totals_and_delta():
    diff, _ = one(line(accrued="100.00"), line(accrued="130.50"))
    assert (diff.base_period, diff.target_period) == ("2026-10", "2026-11")
    assert (diff.total_base, diff.total_target, diff.total_delta) == (
        D("100.00"),
        D("130.50"),
        D("30.50"),
    )


def test_split_into_tariff_volume_other():
    base = line(volume="10", tariff="50.00", accrued="500.00")
    target = line(volume="12", tariff="55.00", accrued="665.00")  # 12 * 55 = 660, 5 рублей сверху
    _, d = one(base, target)
    assert d.delta == D("165.00")
    assert d.delta_tariff == D("50.00")  # (55 - 50) * 10
    assert d.delta_volume == D("110.00")  # (12 - 10) * 55
    assert d.delta_other == D("5.00")
    assert d.delta_tariff + d.delta_volume + d.delta_other == d.delta
    assert d.delta_pct == D("33.0")
    assert "tariff_changed" in d.flags and "growth_over_15pct" in d.flags


def test_split_rounds_to_kopecks():
    base = line(volume="3", tariff="10.001", accrued="30.00")
    target = line(volume="3.3333", tariff="10.0049", accrued="33.35")
    _, d = one(base, target)
    assert d.delta_tariff == D("0.01")  # 0.0039 * 3 = 0.0117 -> 0.01
    assert d.delta_volume == D("3.33")  # 0.3333 * 10.0049 = 3.33463
    assert d.delta_other == D("0.01")  # остаток округления
    assert d.delta_tariff + d.delta_volume + d.delta_other == d.delta


def test_without_volume_everything_is_other():
    _, d = one(line(accrued="100.00"), line(accrued="110.00"))
    assert (d.delta_tariff, d.delta_volume, d.delta_other) == (D("0"), D("0"), D("10.00"))
    assert d.flags == ()


def test_pct_none_when_base_is_zero():
    _, d = one(line(accrued="0.00"), line(accrued="50.00"))
    assert d.delta_pct is None
    assert "growth_over_15pct" not in d.flags


def test_growth_threshold_is_strict():
    _, d = one(line(accrued="100.00"), line(accrued="115.00"))
    assert d.delta_pct == D("15.0") and "growth_over_15pct" not in d.flags
    _, d = one(line(accrued="100.00"), line(accrued="115.10"))
    assert "growth_over_15pct" in d.flags


def test_decrease_has_no_growth_flag():
    _, d = one(line(accrued="100.00"), line(accrued="50.00"))
    assert d.delta == D("-50.00") and d.delta_pct == D("-50.0")
    assert d.flags == ()


def test_new_and_removed_lines():
    base = receipt("2026-10", line("cold_water", "100.00"), line("intercom", "50.00"))
    target = receipt("2026-11", line("cold_water", "100.00"), line("heating", "300.00"))
    diff = compare(base, target)
    assert [x.service_code for x in diff.lines] == ["cold_water", "heating", "intercom"]
    heating, intercom = diff.lines[1], diff.lines[2]
    assert (
        heating.flags == ("new_line",)
        and heating.delta == D("300.00")
        and heating.delta_volume == D("300.00")
    )
    assert heating.accrued_base == D("0") and heating.delta_pct is None
    assert intercom.flags == ("removed_line",) and intercom.delta == D("-50.00")
    assert intercom.accrued_target == D("0") and intercom.delta_pct == D("-100.0")
    assert "heating_season_start" in diff.flags


def test_new_line_keeps_target_flags():
    target = line("other", "20.00", method="norm_increased", recalc="5", name="Пени за просрочку")
    diff = compare(receipt("2026-10"), receipt("2026-11", target))
    assert set(diff.lines[0].flags) == {
        "new_line",
        "norm_increased",
        "has_recalculation",
        "has_penalty",
    }


def test_switched_to_norm_and_norm_increased():
    _, d = one(line(method="meter"), line(method="norm"))
    assert d.flags == ("switched_to_norm",)
    _, d = one(line(method="meter"), line(method="norm_increased"))
    assert set(d.flags) == {"switched_to_norm", "norm_increased"}
    _, d = one(line(method="norm"), line(method="norm"))
    assert d.flags == ()


def test_recalculation_and_penalty_flags():
    _, d = one(line(), line(recalc="-12.00", name="Пени"))
    assert set(d.flags) == {"has_recalculation", "has_penalty"}


def test_tariff_changed_needs_both_tariffs():
    _, d = one(line(tariff="10"), line(tariff="10"))
    assert "tariff_changed" not in d.flags
    _, d = one(line(tariff="10"), line())
    assert "tariff_changed" not in d.flags


def test_tariff_indexation_only_in_indexation_months():
    base, target = (
        line(volume="1", tariff="10", accrued="10"),
        line(volume="1", tariff="11", accrued="11"),
    )
    assert (
        "tariff_indexation" in compare(receipt("2026-09", base), receipt("2026-10", target)).flags
    )
    assert (
        "tariff_indexation" in compare(receipt("2025-12", base), receipt("2026-01", target)).flags
    )
    assert (
        "tariff_indexation"
        not in compare(receipt("2026-10", base), receipt("2026-11", target)).flags
    )
    same = compare(receipt("2026-09", base), receipt("2026-10", base))
    assert "tariff_indexation" not in same.flags


def test_heating_present_in_both_is_not_season_start():
    heating = line("heating", "300.00")
    assert compare(receipt("2026-10", heating), receipt("2026-11", heating)).flags == ()


def test_merge_by_service_sums_duplicates():
    merged = merge_by_service(
        (
            line("other", "10.00", volume="1", tariff="10", method="meter"),
            line("other", "5.00", volume="2", tariff="5", method="norm"),
        )
    )
    m = merged["other"]
    assert (m.accrued, m.volume, m.tariff, m.method) == (D("15.00"), D("3"), D("10"), "norm")


def test_merge_keeps_unknown_volume_unknown():
    merged = merge_by_service((line("other", "10.00", volume="1"), line("other", "5.00")))
    assert merged["other"].volume is None


def test_duplicate_codes_are_compared_as_one():
    base = receipt("2026-10", line("other", "10.00"), line("other", "5.00"))
    target = receipt("2026-11", line("other", "20.00"))
    d = compare(base, target).lines
    assert len(d) == 1 and d[0].accrued_base == D("15.00") and d[0].delta == D("5.00")
