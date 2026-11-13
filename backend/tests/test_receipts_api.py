import base64
import io
import json
import re
from datetime import date
from decimal import Decimal

import httpx
import pytest
from PIL import Image

from app.core.config import get_settings
from tests.conftest import Account, FakeLLM

PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 64
PDF = b"%PDF-1.7\n" + b"0" * 32


async def load_sample(client: httpx.AsyncClient, who: Account, sample: str) -> dict:
    response = await client.post(f"/receipts/samples/{sample}", headers=who.headers)
    assert response.status_code == 200, response.text
    return response.json()


async def test_samples_are_public(client: httpx.AsyncClient):
    samples = (await client.get("/receipts/samples")).json()
    assert [s["id"] for s in samples] == ["2026-09", "2026-10", "2026-11"]
    assert all(s["title"] for s in samples)


async def test_sample_receipt_is_parsed_and_explained(client: httpx.AsyncClient, anna: Account):
    receipt = await load_sample(client, anna, "2026-11")
    assert receipt["status"] == "parsed" and receipt["period"] == "2026-11"
    assert receipt["total"] == "11274.07" and receipt["warnings"] == []
    assert receipt["account_last4"] == "7305" and len(receipt["lines"]) == 7
    water = next(x for x in receipt["lines"] if x["service_code"] == "cold_water")
    assert "Начислено 443,52 ₽" in water["explanation"] and "счётчик" in water["explanation"]
    again = await load_sample(client, anna, "2026-11")
    assert again["id"] == receipt["id"]
    assert len((await client.get("/receipts", headers=anna.headers)).json()) == 1


async def test_unknown_sample_is_404(client: httpx.AsyncClient, anna: Account):
    for sample in ("2030-01", "..%2Fsecret"):
        response = await client.post(f"/receipts/samples/{sample}", headers=anna.headers)
        assert response.status_code == 404


async def test_receipts_are_private(client: httpx.AsyncClient, anna: Account, boris: Account):
    mine = await load_sample(client, anna, "2026-11")
    other = await load_sample(client, boris, "2026-10")
    assert (await client.get("/receipts", headers=boris.headers)).json()[0]["id"] == other["id"]
    for method, url, extra in [
        ("get", f"/receipts/{mine['id']}", {}),
        ("get", f"/receipts/{mine['id']}/check", {}),
        ("patch", f"/receipts/{mine['id']}/lines/1", {"json": {"tariff": "1"}}),
        ("post", f"/receipts/{mine['id']}/recalculation-letter", {"json": {}}),
        ("get", f"/receipts/compare?base={mine['id']}&target={other['id']}", {}),
        ("get", f"/receipts/compare?base={other['id']}&target={mine['id']}", {}),
    ]:
        response = await getattr(client, method)(url, headers=boris.headers, **extra)
        assert response.status_code == 404, url


async def explanation(client: httpx.AsyncClient, who: Account, base: dict, target: dict) -> str:
    params = {"base": base["id"], "target": target["id"]}
    response = await client.get("/receipts/compare/explanation", params=params, headers=who.headers)
    assert response.status_code == 200, response.text
    return response.json()["text"]


async def test_compare_explains_heating_season(client: httpx.AsyncClient, anna: Account):
    october = await load_sample(client, anna, "2026-10")
    november = await load_sample(client, anna, "2026-11")
    response = await client.get(
        "/receipts/compare",
        params={"base": october["id"], "target": november["id"]},
        headers=anna.headers,
    )
    diff = response.json()
    assert diff["total_delta"] == "3287.01" and diff["flags"] == []
    hot = next(x for x in diff["lines"] if x["service_code"] == "hot_water")
    assert hot["flags"] == ["growth_over_15pct", "switched_to_norm", "norm_increased"]
    assert hot["delta"] == "646.56"
    heating = next(x for x in diff["lines"] if x["service_code"] == "heating")
    assert heating["flags"] == ["growth_over_15pct"] and heating["delta_volume"] == "2478.20"
    assert "explanation" not in diff
    text = await explanation(client, anna, october, november)
    assert "выросла на 3287,01 ₽" in text and "Отопление" in text


async def test_compare_september_october_shows_heating_line_and_indexation(
    client: httpx.AsyncClient, anna: Account
):
    september = await load_sample(client, anna, "2026-09")
    october = await load_sample(client, anna, "2026-10")
    diff = (
        await client.get(
            "/receipts/compare",
            params={"base": september["id"], "target": october["id"]},
            headers=anna.headers,
        )
    ).json()
    assert set(diff["flags"]) == {"heating_season_start", "tariff_indexation"}
    assert "отопительный сезон" in await explanation(client, anna, september, october)


async def test_compare_is_instant_and_never_calls_llm(
    client: httpx.AsyncClient, anna: Account, llm: FakeLLM
):
    llm.replies = ["[]"]
    october = await load_sample(client, anna, "2026-10")
    november = await load_sample(client, anna, "2026-11")
    calls = len(llm.calls)
    params = {"base": october["id"], "target": november["id"]}
    assert (await client.get("/receipts/compare", params=params, headers=anna.headers)).is_success
    assert len(llm.calls) == calls


async def test_compare_explanation_is_checked_cached_and_reset_by_edit(
    client: httpx.AsyncClient, anna: Account, llm: FakeLLM
):
    llm.replies = ["[]"]
    october = await load_sample(client, anna, "2026-10")
    november = await load_sample(client, anna, "2026-11")
    llm.replies = ["Отопление подорожало, всего на 3287,01 ₽ больше."]
    calls = len(llm.calls)
    assert await explanation(client, anna, october, november) == llm.replies[0]
    llm.replies = ["Другой текст."]
    assert (
        await explanation(client, anna, october, november)
        == "Отопление подорожало, всего на 3287,01 ₽ больше."
    )
    assert len(llm.calls) == calls + 1  # второй раз из кеша

    await raise_water_tariff(client, anna, november)
    llm.replies = ["Квитанция выросла на 9999 ₽."]
    bad = await explanation(client, anna, october, november)
    assert "9999" not in bad  # правка строки сбросила кеш, текст модели не прошёл проверку


async def test_compare_explanation_without_llm_and_foreign_receipts(
    client: httpx.AsyncClient, anna: Account, boris: Account
):
    october = await load_sample(client, anna, "2026-10")
    november = await load_sample(client, anna, "2026-11")
    assert "3287,01" in await explanation(client, anna, october, november)
    params = {"base": october["id"], "target": november["id"]}
    foreign = await client.get(
        "/receipts/compare/explanation", params=params, headers=boris.headers
    )
    assert foreign.status_code == 404


async def test_check_clean_months_and_norm_increased_finding(
    client: httpx.AsyncClient, anna: Account
):
    for sample in ("2026-09", "2026-10"):
        receipt = await load_sample(client, anna, sample)
        body = (await client.get(f"/receipts/{receipt['id']}/check", headers=anna.headers)).json()
        assert body == {"findings": [], "total_possible_overpayment": "0"}
    november = await load_sample(client, anna, "2026-11")
    body = (await client.get(f"/receipts/{november['id']}/check", headers=anna.headers)).json()
    [finding] = body["findings"]
    assert (finding["type"], finding["service_code"]) == ("norm_increased", "hot_water")
    assert finding["possible_overpayment"] == "619.62" and finding["confidence"] == "medium"


async def raise_water_tariff(client: httpx.AsyncClient, who: Account, receipt: dict) -> dict:
    line = next(x for x in receipt["lines"] if x["service_code"] == "cold_water")
    response = await client.patch(
        f"/receipts/{receipt['id']}/lines/{line['id']}",
        json={"tariff": "70.00"},
        headers=who.headers,
    )
    assert response.status_code == 200, response.text
    return response.json()


async def test_patch_line_recalculates_warnings_and_check(client: httpx.AsyncClient, anna: Account):
    november = await load_sample(client, anna, "2026-11")
    patched = await raise_water_tariff(client, anna, november)
    assert patched["status"] == "needs_review"
    assert "объёмом × тариф" in patched["warnings"][0]
    water = next(x for x in patched["lines"] if x["service_code"] == "cold_water")
    assert "70" in water["explanation"]
    check = (await client.get(f"/receipts/{november['id']}/check", headers=anna.headers)).json()
    finding = check["findings"][0]
    assert (finding["type"], finding["service_code"]) == ("tariff_mismatch", "cold_water")
    expected = (Decimal("70.00") - Decimal("53.4360")) * Decimal("8.30")
    assert Decimal(finding["possible_overpayment"]) == expected.quantize(Decimal("0.01"))
    assert finding["confidence"] == "low"  # тариф воды не подтверждён первоисточником
    assert check["total_possible_overpayment"] == "757.10"  # тариф + повышающий коэффициент


async def test_patch_unknown_line_and_bad_value(client: httpx.AsyncClient, anna: Account):
    november = await load_sample(client, anna, "2026-11")
    missing = await client.patch(
        f"/receipts/{november['id']}/lines/999999", json={"tariff": "1"}, headers=anna.headers
    )
    assert missing.status_code == 404
    bad = await client.patch(
        f"/receipts/{november['id']}/lines/{november['lines'][0]['id']}",
        json={"tariff": "abc"},
        headers=anna.headers,
    )
    assert bad.status_code == 422


async def test_recalculation_letter(client: httpx.AsyncClient, anna: Account):
    november = await load_sample(client, anna, "2026-11")
    await raise_water_tariff(client, anna, november)
    url = f"/receipts/{november['id']}/recalculation-letter"
    request = {"finding_types": ["tariff_mismatch"]}
    letter = (await client.post(url, json=request, headers=anna.headers)).json()["text"]
    for part in (
        "[укажите ФИО]",
        "[укажите номер]",
        "[укажите телефон]",
        "Заявление о перерасчёте",
        "ПП РФ № 354",
    ):
        assert part in letter
    assert (
        "Возможная переплата: 137.48 ₽" in letter
        and "Общая сумма возможной переплаты: 137.48" in letter
    )
    assert "ООО «УПРАВЛЯЮЩАЯ КОМПАНИЯ ЛЕНИНСКОГО РАЙОНА»" in letter and "7305" in letter
    everything = (await client.post(url, json={}, headers=anna.headers)).json()["text"]
    assert "Общая сумма возможной переплаты: 757.10" in everything
    assert "повышающего коэффициента" in everything
    only_other = await client.post(
        url, json={"finding_types": ["duplicate_line"]}, headers=anna.headers
    )
    assert only_other.status_code == 409 and only_other.json()["code"] == "no_findings"
    unknown = await client.post(url, json={"finding_types": ["made_up"]}, headers=anna.headers)
    assert unknown.status_code == 422


async def test_letter_without_findings_is_conflict(client: httpx.AsyncClient, anna: Account):
    november = await load_sample(client, anna, "2026-10")
    response = await client.post(
        f"/receipts/{november['id']}/recalculation-letter", json={}, headers=anna.headers
    )
    assert response.status_code == 409


async def test_upload_without_llm_is_503(client: httpx.AsyncClient, anna: Account):
    response = await client.post(
        "/receipts", files={"file": ("r.png", PNG, "image/png")}, headers=anna.headers
    )
    assert response.status_code == 503 and response.json()["code"] == "llm_unavailable"


async def test_upload_rejects_wrong_type_and_size(client: httpx.AsyncClient, anna: Account):
    text = await client.post(
        "/receipts", files={"file": ("r.pdf", b"hello", "application/pdf")}, headers=anna.headers
    )
    assert text.status_code == 415
    big = PDF + b"0" * (10 * 1024 * 1024)
    response = await client.post(
        "/receipts", files={"file": ("r.pdf", big, "application/pdf")}, headers=anna.headers
    )
    assert response.status_code == 413


PARSED = {
    "period": "2026-11",
    "management_company": {"name": "УК Тест", "inn": "2500000000"},
    "account_last4": "1234567890",
    "area_m2": "40.00",
    "residents": 2,
    "lines": [
        {"service_code": "cold_water", "service_name": "Холодное водоснабжение", "unit": "м3",
         "volume": "5.000", "tariff": "53.4360", "accrued": "267.18", "method": "meter"},
        {"service_code": "maintenance", "service_name": "Содержание", "unit": "м2",
         "volume": "40.00", "tariff": "32.50", "accrued": "1300.00", "method": "norm"},
    ],
    "total": "1567.18",
    "rows_text": [
        "Холодное водоснабжение м3 5,000 53,4360 267,18",
        "Содержание м2 40,00 32,50 1 300,00",
    ],
    "total_text": "Итого 1 567,18",
}  # fmt: skip


async def test_upload_parses_with_llm_and_masks_account(
    client: httpx.AsyncClient, anna: Account, llm: FakeLLM
):
    llm.replies = ["0", json.dumps(PARSED, ensure_ascii=False), "[]"]
    response = await client.post(
        "/receipts", files={"file": ("r.png", PNG, "image/png")}, headers=anna.headers
    )
    assert response.status_code == 201, response.text
    receipt = response.json()
    assert receipt["account_last4"] == "7890" and receipt["status"] == "parsed"
    assert receipt["total"] == "1567.18" and receipt["management_company"]["name"] == "УК Тест"
    assert all(x["explanation"] for x in receipt["lines"])  # без ответа модели — шаблоны
    image = llm.calls[1][1]["content"][1]
    assert image["image_url"]["url"].startswith("data:image/png;base64,")
    assert "7890" not in json.dumps(llm.calls[2], ensure_ascii=False)


async def test_upload_pdf_uses_file_part(client: httpx.AsyncClient, anna: Account, llm: FakeLLM):
    llm.replies = ["0", json.dumps(PARSED, ensure_ascii=False), "[]"]
    response = await client.post(
        "/receipts", files={"file": ("r.pdf", PDF, "application/pdf")}, headers=anna.headers
    )
    assert response.status_code == 201
    assert llm.calls[0][1]["content"][1]["type"] == "file"  # у PDF нет запроса ориентации


async def test_upload_unparsable_llm_answer_is_502(
    client: httpx.AsyncClient, anna: Account, llm: FakeLLM
):
    llm.replies = ["0", "это не JSON"]
    response = await client.post(
        "/receipts", files={"file": ("r.png", PNG, "image/png")}, headers=anna.headers
    )
    assert response.status_code == 502 and response.json()["code"] == "receipt_parse_failed"


async def test_line_explanation_from_llm_must_not_invent_numbers(
    client: httpx.AsyncClient, anna: Account, llm: FakeLLM
):
    llm.replies = ["0", json.dumps(PARSED, ensure_ascii=False), "[]"]
    first = (
        await client.post(
            "/receipts", files={"file": ("r.png", PNG, "image/png")}, headers=anna.headers
        )
    ).json()
    line_id = first["lines"][0]["id"]
    llm.replies = [json.dumps([{"line_id": line_id, "explanation": "Вода, 5 м3 по счётчику."}])]
    patched = (
        await client.patch(
            f"/receipts/{first['id']}/lines/{line_id}", json={"volume": "5"}, headers=anna.headers
        )
    ).json()
    assert patched["lines"][0]["explanation"] == "Вода, 5 м3 по счётчику."
    llm.replies = [json.dumps([{"line_id": line_id, "explanation": "Вода, 99 м3."}])]
    patched = (
        await client.patch(
            f"/receipts/{first['id']}/lines/{line_id}", json={"volume": "5"}, headers=anna.headers
        )
    ).json()
    assert "99" not in patched["lines"][0]["explanation"]


def line(name: str, accrued: str) -> dict:
    return {"service_code": "other", "service_name": name, "accrued": accrued}


def answer(lines: list, rows_count: int, total: str) -> str:
    rows_text = [f"{x['service_name']} {x['accrued']}" for x in lines if "service_name" in x]
    parsed = {
        **PARSED,
        "rows_count": rows_count,
        "lines": lines,
        "total": total,
        "rows_text": rows_text,
        "total_text": f"Итого {total}",
    }
    return json.dumps(parsed, ensure_ascii=False)


async def upload_png(client: httpx.AsyncClient, who: Account, data: bytes = PNG) -> dict:
    response = await client.post(
        "/receipts", files={"file": ("r.png", data, "image/png")}, headers=who.headers
    )
    assert response.status_code == 201, response.text
    return response.json()


async def test_upload_converging_answer_costs_one_model_call(
    client: httpx.AsyncClient, anna: Account, llm: FakeLLM
):
    llm.replies = ["0", answer([line("А", "100.00"), line("Б", "50.00")], 2, "150.00"), "[]"]
    receipt = await upload_png(client, anna)
    assert receipt["status"] == "parsed" and receipt["warnings"] == []
    assert len(llm.calls) == 3  # ориентация, разбор и объяснения строк; повтора нет
    assert "rows_count" in llm.calls[1][0]["content"]


async def test_upload_missing_rows_trigger_one_correcting_pass(
    client: httpx.AsyncClient, anna: Account, llm: FakeLLM
):
    first = answer([line("А", "100.00")], 3, "150.00")
    fixed = answer([line("А", "100.00"), line("Б", "50.00"), line("В", "0.00")], 3, "150.00")
    llm.replies = ["0", first, fixed, "[]"]
    receipt = await upload_png(client, anna)
    assert len(receipt["lines"]) == 3 and receipt["warnings"] == []
    followup = llm.calls[2][-1]["content"]
    assert first in followup and "строк 1, а в таблице 3" in followup
    assert "сумма строк 100.00, итог 150.00" in followup
    assert llm.calls[2][1] == llm.calls[1][1]  # та же картинка


async def test_upload_not_converging_keeps_best_with_warning(
    client: httpx.AsyncClient, anna: Account, llm: FakeLLM
):
    worse = answer([line("А", "100.00")], 4, "500.00")
    better = answer([line("А", "100.00"), line("Б", "300.00")], 4, "500.00")
    llm.replies = ["0", worse, better, "[]"]
    receipt = await upload_png(client, anna)
    assert len(receipt["lines"]) == 2 and receipt["status"] == "needs_review"
    assert any("Распознано строк: 2, в таблице их 4" in w for w in receipt["warnings"])
    assert len(llm.calls) == 4  # ориентация, два разбора и объяснения: разборов не больше двух


async def test_upload_drops_broken_line_with_warning(
    client: httpx.AsyncClient, anna: Account, llm: FakeLLM
):
    broken = {"service_name": "Мусор", "accrued": "не число"}
    llm.replies = ["0", answer([line("А", "100.00"), broken], 2, "100.00"), "[]"]
    receipt = await upload_png(client, anna)
    assert [x["service_name"] for x in receipt["lines"]] == ["А"]
    assert "Не удалось прочитать строку: Мусор" in receipt["warnings"]
    assert receipt["status"] == "needs_review"


async def test_upload_sends_detail_high_and_shrinks_big_image(
    client: httpx.AsyncClient, anna: Account, llm: FakeLLM
):
    big = io.BytesIO()
    Image.new("RGB", (4000, 3000), "white").save(big, format="PNG")
    llm.replies = ["0", answer([line("А", "100.00")], 1, "100.00"), "[]"]
    await upload_png(client, anna, big.getvalue())
    image = llm.calls[1][1]["content"][1]["image_url"]
    assert image["detail"] == "high" and image["url"].startswith("data:image/jpeg;base64,")
    sent = Image.open(io.BytesIO(base64.b64decode(image["url"].split(",", 1)[1])))
    assert max(sent.size) == 2048


async def test_upload_uses_vision_model_from_settings(
    client: httpx.AsyncClient, anna: Account, llm: FakeLLM, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setenv("LLM_PROVIDER", "openai")
    monkeypatch.setenv("LLM_VISION_MODEL", "gpt-4o")
    get_settings.cache_clear()
    try:
        llm.replies = ["0", answer([line("А", "100.00")], 1, "100.00"), "[]"]
        await upload_png(client, anna)
    finally:
        get_settings.cache_clear()
    assert llm.models[:2] == ["gpt-4o", "gpt-4o"]


async def test_implausible_period_is_dropped_with_warning(
    client: httpx.AsyncClient, anna: Account, llm: FakeLLM
):
    for period in ("2016-08", "2999-01"):
        parsed = {**PARSED, "period": period}
        llm.replies = ["0", json.dumps(parsed, ensure_ascii=False), "[]"]
        receipt = await upload_png(client, anna)
        assert receipt["period"] is None and receipt["status"] == "needs_review"
        assert "Не удалось уверенно прочитать период — укажите его." in receipt["warnings"]
    today = date.today().isoformat()
    assert today in llm.calls[1][0]["content"]  # модель знает текущую дату


async def test_receipts_list_is_newest_upload_first(client: httpx.AsyncClient, anna: Account):
    first = await load_sample(client, anna, "2026-11")
    second = await load_sample(client, anna, "2026-09")
    listed = (await client.get("/receipts", headers=anna.headers)).json()
    assert [x["id"] for x in listed] == [second["id"], first["id"]]
    assert listed[0]["period"] == "2026-09"


async def test_upload_ignores_summary_row_returned_as_service(
    client: httpx.AsyncClient, anna: Account, llm: FakeLLM
):
    lines = [line("А", "100.00"), line("Б", "300.00"), line("Итого к оплате", "400.00")]
    llm.replies = ["0", answer(lines, 2, "400.00"), "[]"]
    receipt = await upload_png(client, anna)
    assert [x["service_name"] for x in receipt["lines"]] == ["А", "Б"]
    assert receipt["status"] == "parsed" and len(llm.calls) == 3


def grounded(lines: list, rows_text: list[str], total: str, **extra) -> str:
    parsed = {
        **PARSED,
        "lines": lines,
        "rows_text": rows_text,
        "total": total,
        "total_text": f"Итого {total}",
        **extra,
    }
    return json.dumps(parsed, ensure_ascii=False)


def test_prompt_has_no_example_numbers():
    from app.modules.receipts.parsing import _PROMPT

    assert not re.search(r"\d+[.,]\d+", _PROMPT)


async def test_unreadable_photo_gives_empty_receipt_for_review(
    client: httpx.AsyncClient, anna: Account, llm: FakeLLM
):
    unreadable = json.dumps({"readable": False, "lines": [], "rows_text": []})
    llm.replies = ["0", unreadable, "[]"]
    receipt = await upload_png(client, anna)
    assert receipt["lines"] == [] and receipt["status"] == "needs_review"
    assert any("Не удалось прочитать квитанцию" in w for w in receipt["warnings"])
    assert len(llm.calls) == 2  # повторного разбора нет


async def test_line_missing_from_transcription_is_dropped(
    client: httpx.AsyncClient, anna: Account, llm: FakeLLM
):
    lines = [line("А", "100.00"), line("Выдумка", "777.77")]
    llm.replies = ["0", grounded(lines, ["А 100,00"], "100.00", rows_count=2), "[]"]
    receipt = await upload_png(client, anna)
    assert [x["service_name"] for x in receipt["lines"]] == ["А"]
    assert "Строка не найдена в тексте квитанции: Выдумка" in receipt["warnings"]


async def test_mostly_unconfirmed_lines_need_review(
    client: httpx.AsyncClient, anna: Account, llm: FakeLLM
):
    lines = [line("А", "100.00"), line("Б", "200.00"), line("В", "300.00")]
    reply = grounded(lines, ["А 100,00"], "600.00")
    llm.replies = ["0", reply, reply, "[]"]  # второй разбор тот же
    receipt = await upload_png(client, anna)
    assert receipt["status"] == "needs_review"
    assert any("Не удалось надёжно прочитать" in w for w in receipt["warnings"])


async def test_total_missing_from_total_text_needs_review(
    client: httpx.AsyncClient, anna: Account, llm: FakeLLM
):
    reply = grounded([line("А", "100.00")], ["А 100,00"], "100.00", total_text="Итого 999,99")
    llm.replies = ["0", reply, "[]"]
    receipt = await upload_png(client, anna)
    assert receipt["status"] == "needs_review"
    assert any("Не удалось надёжно прочитать" in w for w in receipt["warnings"])


async def test_amount_due_differs_from_total_without_breaking_sum_check(
    client: httpx.AsyncClient, anna: Account, llm: FakeLLM
):
    reply = grounded(
        [line("А", "100.00"), line("Б", "50.00")],
        ["А 100,00", "Б 50,00"],
        "150.00",
        rows_count=2,
        amount_due="-1366.16",
    )
    llm.replies = ["0", reply, "[]"]
    receipt = await upload_png(client, anna)
    assert receipt["total"] == "150.00" and len(llm.calls) == 3
    assert receipt["warnings"] == ["К оплате с учётом долга или аванса: -1366.16 ₽."]


async def test_multiple_documents_warning(client: httpx.AsyncClient, anna: Account, llm: FakeLLM):
    reply = grounded([line("А", "100.00")], ["А 100,00"], "100.00", multiple_documents=True)
    llm.replies = ["0", reply, "[]"]
    receipt = await upload_png(client, anna)
    assert "На фото несколько квитанций, разобрана одна." in receipt["warnings"]


async def test_rotated_photo_is_turned_before_parsing(
    client: httpx.AsyncClient, anna: Account, llm: FakeLLM
):
    wide = io.BytesIO()
    Image.new("RGB", (400, 200), "white").save(wide, format="PNG")
    llm.replies = ["90", answer([line("А", "100.00")], 1, "100.00"), "[]"]
    await upload_png(client, anna, wide.getvalue())
    assert llm.calls[0][0]["content"][1]["image_url"]["detail"] == "low"
    sent = llm.calls[1][1]["content"][1]["image_url"]["url"]
    assert Image.open(io.BytesIO(base64.b64decode(sent.split(",", 1)[1]))).size == (200, 400)


async def test_non_numeric_orientation_answer_does_not_rotate(
    client: httpx.AsyncClient, anna: Account, llm: FakeLLM
):
    wide = io.BytesIO()
    Image.new("RGB", (400, 200), "white").save(wide, format="PNG")
    llm.replies = ["Текст повёрнут", answer([line("А", "100.00")], 1, "100.00"), "[]"]
    await upload_png(client, anna, wide.getvalue())
    sent = llm.calls[1][1]["content"][1]["image_url"]["url"]
    assert Image.open(io.BytesIO(base64.b64decode(sent.split(",", 1)[1]))).size == (400, 200)
