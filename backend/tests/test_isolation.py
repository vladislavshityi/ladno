"""Изоляция данных: чужой id неотличим от несуществующего на КАЖДОМ маршруте с path-параметром.

Тест обходит все маршруты приложения, поэтому новый эндпоинт без записи в таблицах ниже
роняет его и заставляет подумать о доступе.
"""

import uuid

import httpx
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.main import create_app
from app.modules.houses.models import House
from tests.conftest import PNG, Account, FakeLLM, dev_login
from tests.test_collectives import join, report

# Маршруты, где id — справочник или публичный объект, а не данные жителя.
PUBLIC_PARAMS = {
    "GET /api/categories/{category_id}/questions",
    "GET /api/houses/{house_id}",
    "GET /api/ratings/companies/{company_id}",
    "POST /api/receipts/samples/{sample_id}",
}
# Служебные маршруты бота: доступ по BOT_API_TOKEN, а не по пользователю.
BOT_PREFIX = "/api/bot/"
# Тело запроса там, где без него приходит 422 раньше проверки владельца.
BODIES = {
    "PATCH /api/issues/{issue_id}": {"external_ref": "X-1"},
    "POST /api/issues/{issue_id}/send": {"channel": "email"},
    "PATCH /api/collectives/{collective_id}/membership": {"consent_letter": True},
    "PATCH /api/receipts/{receipt_id}/lines/{line_id}": {"tariff": "1"},
    "POST /api/receipts/{receipt_id}/recalculation-letter": {},
}
# Маршруты без path-параметров, но с чужими id в запросе или теле.
FOREIGN_IN_QUERY_OR_BODY = {
    "GET /api/receipts/compare": ("params", ["base", "target"]),
    "GET /api/receipts/compare/explanation": ("params", ["base", "target"]),
}


def _routes() -> list[tuple[str, str]]:
    """Все методы и пути из схемы OpenAPI: она учитывает вложенные роутеры."""
    paths = create_app().openapi()["paths"]
    return [(m.upper(), p) for p, ops in paths.items() for m in ops if p.startswith("/api/")]


ALL_ROUTES = _routes()
PATH_ROUTES = [
    (m, p)
    for m, p in ALL_ROUTES
    if "{" in p and f"{m} {p}" not in PUBLIC_PARAMS and not p.startswith(BOT_PREFIX)
]
# Публичные эндпоинты: всё остальное без токена должно отвечать 401.
OPEN_ROUTES = {
    "GET /api/health",
    "GET /api/meta",
    "GET /api/faq",
    "GET /api/categories",
    "GET /api/categories/{category_id}/questions",
    "GET /api/addresses/search",
    "GET /api/houses/{house_id}",
    "GET /api/management-companies",
    "GET /api/ratings/companies",
    "GET /api/ratings/companies/{company_id}",
    "GET /api/map/points",
    "GET /api/receipts/samples",
    "GET /api/receipts/services",
    "GET /api/auth/config",
    "POST /api/auth/telegram/widget",
    "POST /api/auth/telegram/webapp",
    "POST /api/auth/dev",
}


@pytest.fixture
async def owner_data(
    client: httpx.AsyncClient, session: AsyncSession, anna: Account, house: House
) -> dict[str, str]:
    """У Анны есть всё: фото, обращение с фото, квитанция и коллективное обращение с соседом."""
    photo = (
        await client.post(
            "/photos", files={"file": ("a.png", PNG, "image/png")}, headers=anna.headers
        )
    ).json()["id"]
    issue = await report(client, anna, house, photo_ids=[photo])
    neighbour = await dev_login(client, 2101)
    neighbour_issue = await report(client, neighbour, house)
    collective = (await join(client, neighbour, neighbour_issue, consent_letter=True)).json()
    receipt = (await client.post("/receipts/samples/2026-11", headers=anna.headers)).json()
    return {
        "issue_id": issue,
        "photo_id": photo,
        "receipt_id": receipt["id"],
        "line_id": str(receipt["lines"][0]["id"]),
        "collective_id": collective["id"],
    }


def _fill(path: str, ids: dict[str, str]) -> str:
    for name, value in ids.items():
        path = path.replace("{" + name + "}", value)
    return path


async def _call(client: httpx.AsyncClient, method: str, path: str, who: Account, ids):
    body = BODIES.get(f"{method} {path}")
    url = _fill(path, ids).removeprefix("/api")
    return await client.request(method, url, headers=who.headers, json=body)


@pytest.mark.parametrize(("method", "path"), PATH_ROUTES)
async def test_foreign_id_looks_like_missing_id(
    client: httpx.AsyncClient,
    boris: Account,
    owner_data: dict[str, str],
    method: str,
    path: str,
):
    unknown = [p for p in path.split("/") if p.startswith("{") and p[1:-1] not in owner_data]
    assert not unknown, f"Добавьте параметр {unknown} в owner_data и проверьте доступ"

    foreign = await _call(client, method, path, boris, owner_data)
    missing_ids = {k: str(uuid.uuid4()) if k != "line_id" else v for k, v in owner_data.items()}
    missing = await _call(client, method, path, boris, missing_ids)
    assert foreign.status_code == 404, foreign.text
    assert foreign.json() == missing.json()


@pytest.mark.parametrize("route", sorted(FOREIGN_IN_QUERY_OR_BODY))
async def test_foreign_receipts_in_query(
    client: httpx.AsyncClient, boris: Account, owner_data: dict[str, str], route: str
):
    method, path = route.split(" ")
    mine = (await client.post("/receipts/samples/2026-10", headers=boris.headers)).json()["id"]
    for base, target in [
        (owner_data["receipt_id"], mine),
        (mine, owner_data["receipt_id"]),
    ]:
        response = await client.request(
            method,
            path.removeprefix("/api"),
            params={"base": base, "target": target},
            headers=boris.headers,
        )
        assert response.status_code == 404


async def test_foreign_ids_in_request_bodies(
    client: httpx.AsyncClient,
    boris: Account,
    owner_data: dict[str, str],
    house: House,
    llm: FakeLLM,
):
    """Чужие id в теле запроса: фото, обращение для присоединения, выбор для ассистента."""
    photo, issue = owner_data["photo_id"], owner_data["issue_id"]
    attempts = [
        ("/issues", {"category": "elevator", "house_id": house.id, "photo_ids": [photo]}),
        ("/issues/classify", {"text": "лифт не работает", "photo_ids": [photo]}),
        ("/collectives/join", {"issue_id": issue, "consent": True}),
        ("/assistant/chat", {"messages": [{"role": "user", "content": "привет"}],
                             "issue_ids": [issue]}),
        ("/assistant/chat", {"messages": [{"role": "user", "content": "привет"}],
                             "receipt_ids": [owner_data["receipt_id"]]}),
    ]  # fmt: skip
    for url, body in attempts:
        response = await client.post(url, json=body, headers=boris.headers)
        assert response.status_code == 404, (url, response.text)


async def test_foreign_data_absent_from_lists_and_exports(
    client: httpx.AsyncClient, boris: Account, owner_data: dict[str, str]
):
    for url in ("/issues", "/receipts", "/users/me/export"):
        text = (await client.get(url, headers=boris.headers)).text
        for value in owner_data.values():
            assert value not in text, url


@pytest.mark.parametrize(("method", "path"), ALL_ROUTES)
async def test_every_closed_route_requires_login(client: httpx.AsyncClient, method: str, path: str):
    key = f"{method} {path}"
    if key in OPEN_ROUTES or (key in PUBLIC_PARAMS and method == "GET"):
        return
    url = path.removeprefix("/api")
    for name in ("issue_id", "photo_id", "receipt_id", "collective_id", "notification_id"):
        url = url.replace("{" + name + "}", str(uuid.uuid4()))
    url = url.replace("{line_id}", "1").replace("{sample_id}", "2026-11")
    url = url.replace("{telegram_id}", "1")
    response = await client.request(method, url)
    assert response.status_code == 401, f"{key} открыт без входа: {response.status_code}"


@pytest.mark.parametrize(
    ("method", "path"), [(m, p) for m, p in ALL_ROUTES if p.startswith(BOT_PREFIX)]
)
async def test_bot_routes_need_bot_token_not_user_token(
    client: httpx.AsyncClient, anna: Account, method: str, path: str
):
    url = path.removeprefix("/api").replace("{telegram_id}", "1")
    url = url.replace("{issue_id}", str(uuid.uuid4())).replace(
        "{notification_id}", str(uuid.uuid4())
    )
    for headers in (
        {},
        anna.headers,
        {"Authorization": "Bearer wrong"},
        {"Authorization": "Bearer "},
    ):
        response = await client.request(method, url, headers=headers)
        assert response.status_code == 401, (path, headers)
