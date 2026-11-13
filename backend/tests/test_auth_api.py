import hashlib
import hmac
import json
import time
from urllib.parse import urlencode

import httpx
import pytest

from tests.conftest import Account, dev_login
from tests.test_telegram import sign_webapp, sign_widget


def now_fields(**over: str) -> dict[str, str]:
    return {"id": "555", "first_name": "Вера", "auth_date": str(int(time.time())), **over}


async def test_config(client: httpx.AsyncClient):
    body = (await client.get("/auth/config")).json()
    assert body == {"telegram_bot_username": "", "dev_login_enabled": True}


async def test_dev_login_and_me(client: httpx.AsyncClient, newcomer: Account):
    me = (await client.get("/users/me", headers=newcomer.headers)).json()
    assert me["id"] == newcomer.id and me["first_name"] == "Тест"
    assert me["consent_required"] is True and me["house"] is None


async def test_dev_login_is_stable_per_telegram_id(client: httpx.AsyncClient, anna: Account):
    again = await dev_login(client, anna.telegram_id)
    assert again.id == anna.id


async def test_dev_login_is_closed_in_prod(client: httpx.AsyncClient, prod_mode: None):
    assert (await client.get("/auth/config")).json()["dev_login_enabled"] is False
    response = await client.post("/auth/dev", json={"telegram_id": 1})
    assert response.status_code == 404 and response.json()["code"] == "not_found"


async def test_widget_login_creates_user_with_first_name_only(client: httpx.AsyncClient):
    fields = now_fields(username="vera_v", photo_url="https://t.me/i/u.jpg", last_name="Иванова")
    body = (await client.post("/auth/telegram/widget", json=sign_widget(fields))).json()
    assert body["token_type"] == "bearer" and body["user"]["first_name"] == "Вера"
    assert set(body["user"]) >= {"id", "first_name", "house", "consent_required"}
    assert "username" not in body["user"] and "last_name" not in body["user"]


async def test_widget_second_login_same_user(client: httpx.AsyncClient):
    first = (await client.post("/auth/telegram/widget", json=sign_widget(now_fields()))).json()
    second = (await client.post("/auth/telegram/widget", json=sign_widget(now_fields()))).json()
    assert first["user"]["id"] == second["user"]["id"]


async def test_widget_forged_hash_rejected(client: httpx.AsyncClient):
    data = sign_widget(now_fields())
    data["id"] = "556"
    response = await client.post("/auth/telegram/widget", json=data)
    assert response.status_code == 401 and response.json()["code"] == "telegram_auth_failed"


async def test_widget_expired_rejected(client: httpx.AsyncClient):
    old = sign_widget(now_fields(auth_date=str(int(time.time()) - 3 * 86400)))
    response = await client.post("/auth/telegram/widget", json=old)
    assert response.status_code == 401


async def test_webapp_login(client: httpx.AsyncClient):
    user = json.dumps({"id": 777, "first_name": "Глеб"}, ensure_ascii=False)
    init_data = sign_webapp({"auth_date": str(int(time.time())), "user": user})
    response = await client.post("/auth/telegram/webapp", json={"init_data": init_data})
    assert response.status_code == 200 and response.json()["user"]["first_name"] == "Глеб"


async def test_webapp_forged_and_widget_signature_rejected(client: httpx.AsyncClient):
    user = json.dumps({"id": 777, "first_name": "Глеб"}, ensure_ascii=False)
    fields = {"auth_date": str(int(time.time())), "user": user}
    forged = sign_webapp(fields, "999:OTHER")
    assert (
        await client.post("/auth/telegram/webapp", json={"init_data": forged})
    ).status_code == 401
    swapped = urlencode(sign_widget(fields))
    assert (
        await client.post("/auth/telegram/webapp", json={"init_data": swapped})
    ).status_code == 401


async def test_telegram_login_not_configured(
    client: httpx.AsyncClient, monkeypatch: pytest.MonkeyPatch
):
    from app.core.config import get_settings

    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "")
    get_settings.cache_clear()
    try:
        response = await client.post("/auth/telegram/widget", json=sign_widget(now_fields()))
    finally:
        monkeypatch.undo()
        get_settings.cache_clear()
    assert response.status_code == 503 and response.json()["code"] == "telegram_not_configured"


async def test_protected_endpoints_need_token(client: httpx.AsyncClient):
    for method, url in [("get", "/users/me"), ("get", "/issues"), ("get", "/receipts"),
                        ("post", "/photos"), ("post", "/assistant/chat")]:  # fmt: skip
        response = await getattr(client, method)(url)
        assert response.status_code == 401, url
        assert response.json()["code"] == "not_authenticated"


async def test_garbage_and_foreign_signed_token_rejected(client: httpx.AsyncClient):
    for token in ("garbage", hmac.new(b"x", b"y", hashlib.sha256).hexdigest()):
        response = await client.get("/users/me", headers={"Authorization": f"Bearer {token}"})
        assert response.status_code == 401 and response.json()["code"] == "invalid_token"


async def test_public_endpoints_do_not_need_token(client: httpx.AsyncClient):
    for url in ["/health", "/categories", "/addresses/search?q=Кутузова", "/management-companies",
                "/receipts/samples", "/auth/config"]:  # fmt: skip
        assert (await client.get(url)).status_code == 200, url
