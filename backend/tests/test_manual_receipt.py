import httpx

from tests.conftest import Account

HEADER = {"period": "2026-11", "management_company": {"name": "ООО «УК»", "inn": "2540111333"}}
WATER = {
    "service_code": "cold_water",
    "service_name": "Холодное водоснабжение",
    "unit": "м3",
    "volume": "8.30",
    "tariff": "60.00",
    "accrued": "498.00",
    "method": "meter",
}


async def create_manual(client: httpx.AsyncClient, who: Account, **payload) -> httpx.Response:
    body = {**HEADER, "lines": [WATER], **payload}
    return await client.post("/receipts/manual", json=body, headers=who.headers)


async def test_manual_receipt_is_stored_and_explained(client: httpx.AsyncClient, anna: Account):
    response = await create_manual(client, anna, area_m2="54.30", residents=3, account_last4="7305")
    assert response.status_code == 201, response.text
    receipt = response.json()
    assert receipt["period"] == "2026-11" and receipt["total"] == "498.00"
    assert receipt["status"] == "parsed" and receipt["warnings"] == []
    assert receipt["management_company"]["inn"] == "2540111333"
    assert receipt["account_last4"] == "7305" and receipt["lines"][0]["explanation"]
    assert len((await client.get("/receipts", headers=anna.headers)).json()) == 1


async def test_manual_receipt_warns_about_mismatches(client: httpx.AsyncClient, anna: Account):
    wrong_line = {**WATER, "accrued": "100.00"}
    receipt = (await create_manual(client, anna, lines=[wrong_line], total="999.00")).json()
    assert receipt["status"] == "needs_review"
    assert any("не совпадает с объёмом × тариф" in w for w in receipt["warnings"])
    assert any("Сумма строк не совпадает с итогом" in w for w in receipt["warnings"])


async def test_manual_receipt_validation(client: httpx.AsyncClient, anna: Account):
    for payload in (
        {"lines": []},
        {"period": "2026-13"},
        {"residents": -1},
        {"account_last4": "00127305"},
    ):
        assert (await create_manual(client, anna, **payload)).status_code == 422
    unauthorized = await client.post("/receipts/manual", json={**HEADER, "lines": [WATER]})
    assert unauthorized.status_code == 401


async def test_services_catalog_substitutes_tariff(client: httpx.AsyncClient):
    options = (await client.get("/receipts/services", params={"period": "2026-11"})).json()
    by_code = {x["service_code"]: x for x in options}
    assert len(options) == 13 and by_code["cold_water"]["tariff"] == "53.4360"
    assert by_code["electricity"]["tariff"] is None  # два варианта тарифа: не угадываем
    assert by_code["intercom"]["tariff"] is None
    empty = (await client.get("/receipts/services")).json()
    assert all(x["tariff"] is None for x in empty)
