import httpx
import pytest

from tests.conftest import Account

DARK = {"category": "stairwell_lighting", "answers": {"scope": "floor", "duration": "week_plus"}}
CUSTOM = {"custom_address": "г Владивосток, ул Новая, д 1", "custom_company_name": "ТСЖ «Новое»"}


async def set_profile(client: httpx.AsyncClient, who: Account, **profile) -> httpx.Response:
    return await client.put("/users/me/profile", json=profile, headers=who.headers)


async def test_profile_keeps_custom_address_and_company(client: httpx.AsyncClient, anna: Account):
    body = (await set_profile(client, anna, **CUSTOM)).json()
    assert body["custom_address"] == CUSTOM["custom_address"] and body["house"] is None
    assert body["custom_company_name"] == "ТСЖ «Новое»" and body["management_company"] is None


async def test_custom_company_beats_house_company(client: httpx.AsyncClient, anna: Account):
    hit = (await client.get("/addresses/search", params={"q": "Кутузова 5а"})).json()[0]
    body = (
        await set_profile(
            client, anna, house_id=hit["house_id"], custom_company_name="  ТСЖ «Новое»  "
        )
    ).json()
    assert body["house"]["id"] == hit["house_id"] and body["management_company"] is None
    assert body["custom_company_name"] == "ТСЖ «Новое»"


@pytest.mark.parametrize(
    "pair",
    [
        {"house_id": 1, "custom_address": "г Владивосток, ул Новая, д 1"},
        {"management_company_id": 1, "custom_company_name": "ТСЖ"},
    ],
)
async def test_exactly_one_of_each_pair(client: httpx.AsyncClient, anna: Account, pair: dict):
    response = await set_profile(client, anna, **pair)
    assert response.status_code == 422 and response.json()["code"] == "validation_error"


async def test_route_and_letter_work_with_custom_values(client: httpx.AsyncClient, anna: Account):
    await set_profile(client, anna, full_name="Иванов И. И.", **CUSTOM)
    route = (await client.post("/issues/route", json=DARK, headers=anna.headers)).json()
    assert route["addressee"]["name"] == "ТСЖ «Новое»"
    assert [c["type"] for c in route["addressee"]["channels"]] == ["pos"]
    assert route["explanation"].endswith(
        "Контакты УК не найдены в справочнике, уточните у соседей или на сайте УК."
    )
    issue = (await client.post("/issues", json=DARK, headers=anna.headers)).json()
    full = issue["draft"]["full"]
    assert issue["house_id"] is None and issue["address"] == CUSTOM["custom_address"]
    assert "Кому: ТСЖ «Новое»" in full and f"Адрес: {CUSTOM['custom_address']}" in full
    second = (await client.post(f"/issues/{issue['id']}/escalate", headers=anna.headers)).json()
    assert second["address"] == CUSTOM["custom_address"]
    assert f"Адрес: {CUSTOM['custom_address']}" in second["draft"]["full"]


async def test_issue_accepts_its_own_custom_address(client: httpx.AsyncClient, anna: Account):
    body = {**DARK, "custom_address": "г Владивосток, ул Другая, д 9"}
    issue = (await client.post("/issues", json=body, headers=anna.headers)).json()
    assert issue["address"] == "г Владивосток, ул Другая, д 9" and issue["house_id"] is None
    assert "укажите её в профиле" in issue["route"]["addressee"]["name"]
    both = await client.post("/issues", json={**body, "house_id": 1}, headers=anna.headers)
    assert both.status_code == 422


async def test_user_export_and_ordinary_flow_unchanged(client: httpx.AsyncClient, anna: Account):
    hit = (await client.get("/addresses/search", params={"q": "Кутузова 5а"})).json()[0]
    body = (await set_profile(client, anna, house_id=hit["house_id"])).json()
    assert body["custom_address"] is None and body["management_company"]["source"] in (
        "gis_zhkh",
        "vl_ru",
        None,
    )
