"""Сценарии без языковой модели (LLM_PROVIDER=none): всё работает по справочникам и шаблонам."""

import httpx

from app.core.config import get_settings
from tests.conftest import Account, dev_login
from tests.test_manual_receipt import HEADER, WATER


async def test_issue_from_text_to_pdf_without_llm(client: httpx.AsyncClient):
    assert get_settings().llm_provider == "none"
    who = await dev_login(client, 7001)
    text = "В подъезде не горит свет на третьем этаже"

    classified = (
        await client.post("/issues/classify", json={"text": text}, headers=who.headers)
    ).json()
    assert classified["category"] == "stairwell_lighting"
    assert classified["needs_manual_choice"] is False

    answers = {"scope": "floor", "duration": "week_plus"}
    created = await client.post(
        "/issues",
        json={"category": classified["category"], "answers": answers, "description": text},
        headers=who.headers,
    )
    assert created.status_code == 201, created.text
    issue = created.json()
    assert text in issue["draft"]["full"] and "Освещение" in issue["draft"]["full"]
    assert "больше недели" in issue["draft"]["full"]

    pdf = await client.get(f"/issues/{issue['id']}/letter.pdf", headers=who.headers)
    assert pdf.status_code == 200 and pdf.content.startswith(b"%PDF")


async def test_manual_receipt_to_recalculation_letter_without_llm(
    client: httpx.AsyncClient, anna: Account
):
    manual = await client.post(
        "/receipts/manual", json={**HEADER, "lines": [WATER]}, headers=anna.headers
    )
    assert manual.status_code == 201, manual.text
    receipt = manual.json()

    check = (await client.get(f"/receipts/{receipt['id']}/check", headers=anna.headers)).json()
    assert [f["type"] for f in check["findings"]] == ["tariff_mismatch"]
    assert check["total_possible_overpayment"] == "54.48"

    letter = await client.post(
        f"/receipts/{receipt['id']}/recalculation-letter", json={}, headers=anna.headers
    )
    assert letter.status_code == 200
    assert "Заявление о перерасчёте" in letter.json()["text"]
    assert "54.48" in letter.json()["text"]
