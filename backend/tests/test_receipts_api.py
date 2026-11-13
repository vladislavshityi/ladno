import json
from decimal import Decimal

import httpx

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


async def test_list_is_sorted_by_period_desc(client: httpx.AsyncClient, anna: Account):
    for sample in ("2026-10", "2026-11", "2026-09"):
        await load_sample(client, anna, sample)
    periods = [r["period"] for r in (await client.get("/receipts", headers=anna.headers)).json()]
    assert periods == ["2026-11", "2026-10", "2026-09"]


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
}  # fmt: skip


async def test_upload_parses_with_llm_and_masks_account(
    client: httpx.AsyncClient, anna: Account, llm: FakeLLM
):
    llm.replies = [json.dumps(PARSED, ensure_ascii=False), "[]"]
    response = await client.post(
        "/receipts", files={"file": ("r.png", PNG, "image/png")}, headers=anna.headers
    )
    assert response.status_code == 201, response.text
    receipt = response.json()
    assert receipt["account_last4"] == "7890" and receipt["status"] == "parsed"
    assert receipt["total"] == "1567.18" and receipt["management_company"]["name"] == "УК Тест"
    assert all(x["explanation"] for x in receipt["lines"])  # без ответа модели — шаблоны
    image = llm.calls[0][1]["content"][1]
    assert image["image_url"]["url"].startswith("data:image/png;base64,")
    assert "7890" not in json.dumps(llm.calls[1], ensure_ascii=False)


async def test_upload_pdf_uses_file_part(client: httpx.AsyncClient, anna: Account, llm: FakeLLM):
    llm.replies = [json.dumps(PARSED, ensure_ascii=False), "[]"]
    response = await client.post(
        "/receipts", files={"file": ("r.pdf", PDF, "application/pdf")}, headers=anna.headers
    )
    assert response.status_code == 201
    assert llm.calls[0][1]["content"][1]["type"] == "file"


async def test_upload_unparsable_llm_answer_is_502(
    client: httpx.AsyncClient, anna: Account, llm: FakeLLM
):
    llm.replies = ["это не JSON"]
    response = await client.post(
        "/receipts", files={"file": ("r.png", PNG, "image/png")}, headers=anna.headers
    )
    assert response.status_code == 502 and response.json()["code"] == "receipt_parse_failed"


async def test_line_explanation_from_llm_must_not_invent_numbers(
    client: httpx.AsyncClient, anna: Account, llm: FakeLLM
):
    llm.replies = [json.dumps(PARSED, ensure_ascii=False), "[]"]
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
