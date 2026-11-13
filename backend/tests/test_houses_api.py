import httpx
import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.houses.models import House
from tests.conftest import Account


async def suggest(client: httpx.AsyncClient, q: str) -> list[str]:
    response = await client.get("/addresses/search", params={"q": q})
    assert response.status_code == 200, response.text
    return [h["address"] for h in response.json()]


async def test_search_real_data(client: httpx.AsyncClient):
    assert await suggest(client, "Кутузова 5а") == ["г Владивосток, ул Кутузова, д 5а"]
    assert await suggest(client, "кутузова, 5 а") == ["г Владивосток, ул Кутузова, д 5а"]
    assert (await suggest(client, "Кутузова 5"))[0] == "г Владивосток, ул Кутузова, д 5"
    assert (await suggest(client, "Светланкая 10"))[0] == "г Владивосток, ул Светланская, д 10"
    assert all("2-я Поселковая" in a for a in await suggest(client, "2-я Поселковая"))


async def test_search_nothing_found(client: httpx.AsyncClient):
    assert await suggest(client, "!!!") == []
    assert await suggest(client, "нет такой улицы zzz") == []


async def test_search_validates_query(client: httpx.AsyncClient):
    assert (await client.get("/addresses/search")).status_code == 422
    assert (await client.get("/addresses/search", params={"q": ""})).status_code == 422


async def test_house_by_id_with_company(client: httpx.AsyncClient):
    hits = (await client.get("/addresses/search", params={"q": "Кутузова 5а"})).json()
    house = (await client.get(f"/houses/{hits[0]['house_id']}")).json()
    assert house["address"] == hits[0]["address"]
    assert house["lat"] is not None and house["management_company"]["name"]


async def test_unknown_house_is_404(client: httpx.AsyncClient):
    response = await client.get("/houses/99999999")
    assert response.status_code == 404 and response.json()["code"] == "not_found"


async def test_companies_list_and_search(client: httpx.AsyncClient):
    everything = (await client.get("/management-companies")).json()
    assert len(everything) == 20
    found = (await client.get("/management-companies", params={"q": "дВкС"})).json()
    assert found and all("двкс" in c["name"].lower() for c in found)
    assert (await client.get("/management-companies", params={"q": "%_zzz"})).json() == []


async def test_companies_found_by_inn(client: httpx.AsyncClient):
    found = (await client.get("/management-companies", params={"inn": "2537068720"})).json()
    assert [c["name"] for c in found] == ["ООО «ДВКС»"]
    assert (await client.get("/management-companies", params={"inn": "0000000000"})).json() == []


@pytest.mark.parametrize("source", ["gis_zhkh", "vl_ru"])
async def test_company_source_comes_from_house_link(
    client: httpx.AsyncClient, session: AsyncSession, source: str
):
    stmt = select(House.id).where(House.management_company_source == source).limit(1)
    house = (await client.get(f"/houses/{await session.scalar(stmt)}")).json()
    assert house["management_company"]["source"] == source
    assert "management_company_source" not in house
    assert all(c["source"] is None for c in (await client.get("/management-companies")).json())


async def test_profile_company_source_follows_house_company(
    client: httpx.AsyncClient, session: AsyncSession, anna: Account
):
    stmt = select(House).where(House.management_company_source == "vl_ru").limit(1)
    house = await session.scalar(stmt)
    profile = {"house_id": house.id}
    me = (await client.put("/users/me/profile", json=profile, headers=anna.headers)).json()
    assert me["management_company"]["source"] == "vl_ru"
    other = house.management_company_id % 400 + 1
    profile = {"house_id": house.id, "management_company_id": other}
    me = (await client.put("/users/me/profile", json=profile, headers=anna.headers)).json()
    assert me["management_company"]["source"] is None  # выбрана жителем
