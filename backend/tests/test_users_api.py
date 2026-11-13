from pathlib import Path

import httpx
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.issues.models import Photo
from app.modules.users.models import User
from tests.conftest import Account


async def house_with_company(client: httpx.AsyncClient) -> dict:
    hits = (await client.get("/addresses/search", params={"q": "Кутузова 5а"})).json()
    return (await client.get(f"/houses/{hits[0]['house_id']}")).json()


async def test_profile_takes_company_from_house(client: httpx.AsyncClient, anna: Account):
    house = await house_with_company(client)
    body = (
        await client.put(
            "/users/me/profile",
            json={"house_id": house["id"], "entrance": "2"},
            headers=anna.headers,
        )
    ).json()
    assert body["house"]["id"] == house["id"] and body["entrance"] == "2"
    assert body["management_company"]["id"] == house["management_company"]["id"]
    me = (await client.get("/users/me", headers=anna.headers)).json()
    assert me["management_company"]["name"] == house["management_company"]["name"]


async def test_profile_explicit_company_wins(client: httpx.AsyncClient, anna: Account):
    house = await house_with_company(client)
    other = (await client.get("/management-companies", params={"q": "ДВКС"})).json()[0]
    body = (
        await client.put(
            "/users/me/profile",
            json={"house_id": house["id"], "management_company_id": other["id"]},
            headers=anna.headers,
        )
    ).json()
    assert body["management_company"]["id"] == other["id"]


async def test_profile_unknown_house_and_company(client: httpx.AsyncClient, anna: Account):
    for payload in ({"house_id": 99999999}, {"management_company_id": 99999999}):
        response = await client.put("/users/me/profile", json=payload, headers=anna.headers)
        assert response.status_code == 404


async def test_consent_flow(client: httpx.AsyncClient, newcomer: Account):
    anna = newcomer
    wrong = await client.post("/users/me/consent", json={"version": "old"}, headers=anna.headers)
    assert wrong.status_code == 409 and wrong.json()["code"] == "consent_version_mismatch"
    ok = await client.post("/users/me/consent", json={"version": "2026-11"}, headers=anna.headers)
    body = ok.json()
    assert body["consent_required"] is False and body["consent_version"] == "2026-11"
    assert body["consent_at"] is not None


async def test_delete_account_removes_everything(
    client: httpx.AsyncClient, session: AsyncSession, anna: Account, boris: Account
):
    await client.post("/receipts/samples/2026-10", headers=anna.headers)
    await client.post(
        "/issues", json={"category": "graffiti", "answers": {"place": "stop"}}, headers=anna.headers
    )
    response = await client.delete("/users/me", headers=anna.headers)
    assert response.status_code == 204
    assert (await client.get("/users/me", headers=anna.headers)).status_code == 401
    assert await session.scalar(select(func.count()).select_from(User)) == 1
    assert (await client.get("/issues", headers=boris.headers)).json() == []


async def test_delete_account_removes_photo_files(
    client: httpx.AsyncClient, session: AsyncSession, anna: Account
):
    png = b"\x89PNG\r\n\x1a\n" + b"\x00" * 16
    await client.post("/photos", files={"file": ("a.png", png, "image/png")}, headers=anna.headers)
    path = Path(await session.scalar(select(Photo.path)))
    assert path.is_file()  # noqa: ASYNC240
    await client.delete("/users/me", headers=anna.headers)
    assert not path.exists()  # noqa: ASYNC240


async def test_personal_data_requires_consent(
    client: httpx.AsyncClient, newcomer: Account, anna: Account
):
    storing = [
        ("put", "/users/me/profile", {"json": {"full_name": "Иванов И. И."}}),
        ("post", "/issues", {"json": {"category": "graffiti"}}),
        ("post", "/photos", {"files": {"file": ("a.png", b"\x89PNG\r\n\x1a\n", "image/png")}}),
        ("post", "/receipts/samples/2026-10", {}),
        ("post", "/receipts", {"files": {"file": ("a.png", b"\x89PNG\r\n\x1a\n", "image/png")}}),
    ]
    for method, url, extra in storing:
        response = await getattr(client, method)(url, headers=newcomer.headers, **extra)
        assert response.status_code == 403, url
        assert response.json()["code"] == "consent_required"
    # чтение, согласие, экспорт и удаление доступны и без согласия
    assert (await client.get("/users/me", headers=newcomer.headers)).status_code == 200
    assert (await client.get("/users/me/export", headers=newcomer.headers)).status_code == 200
    assert (await client.delete("/users/me", headers=newcomer.headers)).status_code == 204
    assert (await client.get("/users/me", headers=anna.headers)).status_code == 200


async def test_profile_personal_data_goes_into_letters_by_code(
    client: httpx.AsyncClient, anna: Account
):
    profile = {"full_name": "Иванов И. И.", "phone": "+79990001122", "email": "i@example.ru",
               "apartment": "12"}  # fmt: skip
    body = (await client.put("/users/me/profile", json=profile, headers=anna.headers)).json()
    assert body["full_name"] == "Иванов И. И." and body["apartment"] == "12"
    issue = (
        await client.post("/issues", json={"category": "graffiti"}, headers=anna.headers)
    ).json()
    full = issue["draft"]["full"]
    assert "От: Иванов И. И., кв. 12, тел. +79990001122, e-mail i@example.ru" in full
    assert "[укажите" not in full and "Иванов" not in issue["draft"]["pos_short"]
    receipt = (await client.post("/receipts/samples/2026-11", headers=anna.headers)).json()
    url = f"/receipts/{receipt['id']}/recalculation-letter"
    letter = (await client.post(url, json={}, headers=anna.headers)).json()["text"]
    assert "От: Иванов И. И., кв. 12" in letter


async def test_partial_profile_keeps_placeholders(client: httpx.AsyncClient, anna: Account):
    await client.put("/users/me/profile", json={"full_name": "Петров П. П."}, headers=anna.headers)
    issue = (
        await client.post("/issues", json={"category": "graffiti"}, headers=anna.headers)
    ).json()
    assert "От: Петров П. П., кв. [укажите номер], тел. [укажите телефон]" in issue["draft"]["full"]


async def test_personal_data_never_goes_to_llm(client: httpx.AsyncClient, anna: Account, llm):
    profile = {"full_name": "Сидоров С. С.", "phone": "+79991112233", "email": "s@example.ru",
               "apartment": "77"}  # fmt: skip
    await client.put("/users/me/profile", json=profile, headers=anna.headers)
    llm.replies = ["[]"]
    await client.post("/receipts/samples/2026-11", headers=anna.headers)
    await client.post("/issues", json={"category": "graffiti"}, headers=anna.headers)
    llm.chunks = ["ок"]
    await client.post(
        "/assistant/chat",
        json={"messages": [{"role": "user", "content": "привет"}]},
        headers=anna.headers,
    )
    sent = str(llm.calls)
    assert llm.calls
    for secret in ("Сидоров", "79991112233", "s@example.ru", '"77"'):
        assert secret not in sent


async def test_export_contains_all_own_data(
    client: httpx.AsyncClient, anna: Account, boris: Account
):
    await client.put("/users/me/profile", json={"full_name": "Иванов"}, headers=anna.headers)
    await client.post("/issues", json={"category": "graffiti"}, headers=anna.headers)
    await client.post("/receipts/samples/2026-10", headers=anna.headers)
    png = b"\x89PNG\r\n\x1a\n" + b"\x00" * 8
    await client.post("/photos", files={"file": ("a.png", png, "image/png")}, headers=anna.headers)
    await client.post("/issues", json={"category": "pothole"}, headers=boris.headers)
    data = (await client.get("/users/me/export", headers=anna.headers)).json()
    assert data["profile"]["full_name"] == "Иванов"
    assert [i["category"] for i in data["issues"]] == ["graffiti"]
    assert data["issues"][0]["draft"]["full"]
    assert [r["period"] for r in data["receipts"]] == ["2026-10"]
    assert len(data["receipts"][0]["lines"]) == 7 and len(data["photos"]) == 1
