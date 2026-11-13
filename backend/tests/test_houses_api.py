import httpx


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
