"""Лимиты на пользователя, общий бюджет модели, кэши и защита от массовых входов."""

import json
from collections.abc import Callable

import httpx
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.llm.client import OllamaClient, OpenAICompatibleClient
from app.llm.tokens import tokens_today
from tests.conftest import PNG, Account, FakeLLM, dev_login
from tests.test_auth_api import now_fields, sign_widget
from tests.test_receipts_api import PARSED

CLASSIFIED = '{"category": "pothole", "confidence": 0.9}'


@pytest.fixture
def settings(monkeypatch: pytest.MonkeyPatch) -> Callable[..., None]:
    """Меняет настройки на время теста: settings(LLM_CLASSIFY_PER_HOUR=2)."""

    def apply(**env: object) -> None:
        for name, value in env.items():
            monkeypatch.setenv(name, str(value))
        get_settings.cache_clear()

    yield apply
    monkeypatch.undo()
    get_settings.cache_clear()


async def classify(client: httpx.AsyncClient, who: Account, text: str) -> httpx.Response:
    return await client.post("/issues/classify", json={"text": text}, headers=who.headers)


# --- лимиты на пользователя ---


async def test_classify_limit_returns_429_with_retry_time(
    client: httpx.AsyncClient, anna: Account, boris: Account, llm: FakeLLM, settings
):
    settings(LLM_CLASSIFY_PER_HOUR=2)
    llm.replies = [CLASSIFIED]
    assert (await classify(client, anna, "яма на дороге 1")).status_code == 200
    assert (await classify(client, anna, "яма на дороге 2")).status_code == 200
    limited = await classify(client, anna, "яма на дороге 3")
    assert limited.status_code == 429 and limited.json()["code"] == "quota_exceeded"
    assert "не больше 2 определений категории за час" in limited.json()["detail"]
    assert "Снова можно через" in limited.json()["detail"]
    assert 0 < int(limited.headers["Retry-After"]) <= 3600
    assert (await classify(client, boris, "яма на дороге 3")).status_code == 200  # лимит личный


async def test_classify_without_model_is_not_limited(
    client: httpx.AsyncClient, anna: Account, settings
):
    settings(LLM_CLASSIFY_PER_HOUR=1)
    for number in range(3):
        assert (await classify(client, anna, f"яма на дороге {number}")).status_code == 200


async def test_zero_limit_means_unlimited(
    client: httpx.AsyncClient, anna: Account, llm: FakeLLM, settings
):
    settings(LLM_CLASSIFY_PER_HOUR=0)
    llm.replies = [CLASSIFIED]
    for number in range(3):
        assert (await classify(client, anna, f"яма на дороге {number}")).status_code == 200


async def test_assistant_daily_limit(
    client: httpx.AsyncClient, anna: Account, llm: FakeLLM, settings
):
    settings(LLM_ASSISTANT_PER_DAY=1)
    llm.chunks = ["Привет"]
    body = {"messages": [{"role": "user", "content": "Как подать жалобу?"}]}
    assert (
        await client.post("/assistant/chat", json=body, headers=anna.headers)
    ).status_code == 200
    second = await client.post("/assistant/chat", json=body, headers=anna.headers)
    assert second.status_code == 429 and "за сутки" in second.json()["detail"]


async def test_photo_and_issue_daily_limits(client: httpx.AsyncClient, anna: Account, settings):
    settings(PHOTOS_PER_DAY=1, ISSUES_PER_DAY=1)
    upload = {"files": {"file": ("a.png", PNG, "image/png")}, "headers": anna.headers}
    assert (await client.post("/photos", **upload)).status_code == 201
    assert (await client.post("/photos", **upload)).status_code == 429
    issue = {"category": "elevator", "description": "Лифт не работает"}
    assert (await client.post("/issues", json=issue, headers=anna.headers)).status_code == 201
    assert (await client.post("/issues", json=issue, headers=anna.headers)).status_code == 429


async def test_manual_receipt_limit(client: httpx.AsyncClient, anna: Account, settings):
    from tests.test_manual_receipt import create_manual

    settings(LLM_RECEIPT_TEXTS_PER_DAY=1)
    assert (await create_manual(client, anna)).status_code == 201
    assert (await create_manual(client, anna)).status_code == 429


# --- общий бюджет ---


async def test_budget_exhaustion_switches_to_templates_and_shows_in_meta(
    client: httpx.AsyncClient, anna: Account, llm: FakeLLM, settings
):
    settings(LLM_DAILY_REQUEST_BUDGET=2)
    llm.replies = [CLASSIFIED]
    assert (await client.get("/meta")).json()["llm_budget_exhausted"] is False

    first = await classify(client, anna, "яма на дороге возле дома")
    second = await classify(client, anna, "яма на дороге у школы")
    assert first.json()["category"] == "pothole"
    assert second.json()["category"] == "pothole"
    assert (await client.get("/meta")).json()["llm_budget_exhausted"] is True

    calls = len(llm.calls)
    third = await classify(client, anna, "яма на дороге во дворе")  # модель недоступна
    assert third.status_code == 200 and len(llm.calls) == calls
    assert third.json()["category"] == "pothole"  # ключевые слова из справочника


async def test_budget_exhausted_assistant_is_unavailable_not_failing(
    client: httpx.AsyncClient, anna: Account, llm: FakeLLM, settings
):
    settings(LLM_DAILY_REQUEST_BUDGET=1)
    llm.chunks = ["Ответ"]
    body = {"messages": [{"role": "user", "content": "Как подать жалобу?"}]}
    assert (
        await client.post("/assistant/chat", json=body, headers=anna.headers)
    ).status_code == 200
    response = await client.post("/assistant/chat", json=body, headers=anna.headers)
    assert response.status_code == 503 and response.json()["code"] == "llm_unavailable"


async def test_issue_is_created_from_template_when_budget_is_spent(
    client: httpx.AsyncClient, anna: Account, llm: FakeLLM, settings
):
    settings(LLM_DAILY_REQUEST_BUDGET=1)
    llm.replies = ["Лифт в доме не работает уже неделю."]
    issue = {"category": "elevator", "description": "Лифт не работает"}
    for _ in range(2):
        assert (await client.post("/issues", json=issue, headers=anna.headers)).status_code == 201
    assert len(llm.calls) == 1


async def test_counters_survive_in_database(
    client: httpx.AsyncClient, session: AsyncSession, anna: Account, llm: FakeLLM, settings
):
    from sqlalchemy import select

    from app.core.quota import LlmUsage

    llm.replies = [CLASSIFIED]
    await classify(client, anna, "яма на дороге возле дома")
    rows = {(r.kind, r.subject): r.requests for r in await session.scalars(select(LlmUsage))}
    assert rows == {("classify", anna.id): 1, ("budget", "global"): 1}


# --- кэши ---


async def test_same_text_is_classified_once(
    client: httpx.AsyncClient, anna: Account, boris: Account, llm: FakeLLM, settings
):
    settings(LLM_CLASSIFY_PER_HOUR=1)
    llm.replies = [CLASSIFIED]
    first = await classify(client, anna, "Яма на  дороге у дома")
    again = await classify(client, anna, "яма на дороге у дома ")  # другой регистр и пробелы
    other_user = await classify(client, boris, "яма на дороге у дома")
    assert first.json() == again.json() == other_user.json()
    assert len(llm.calls) == 1  # повторы не вызвали модель и не потратили лимит


async def test_same_receipt_file_is_parsed_once(
    client: httpx.AsyncClient, anna: Account, boris: Account, llm: FakeLLM, settings
):
    settings(LLM_RECEIPT_SCANS_PER_DAY=1)
    llm.replies = ["0", json.dumps(PARSED, ensure_ascii=False), "[]"]
    files = {"file": ("r.png", PNG, "image/png")}
    first = await client.post("/receipts", files=files, headers=anna.headers)
    calls = len(llm.calls)
    again = await client.post("/receipts", files=files, headers=anna.headers)
    assert first.status_code == again.status_code == 201
    assert first.json()["id"] == again.json()["id"] and len(llm.calls) == calls
    assert len((await client.get("/receipts", headers=anna.headers)).json()) == 1
    llm.replies = ["0", json.dumps(PARSED, ensure_ascii=False), "[]"]
    other_user = await client.post("/receipts", files=files, headers=boris.headers)
    assert other_user.json()["id"] != first.json()["id"]  # чужой разбор не отдаётся


async def test_receipt_scan_limit(client: httpx.AsyncClient, anna: Account, llm: FakeLLM, settings):
    settings(LLM_RECEIPT_SCANS_PER_DAY=1)
    llm.replies = ["0", json.dumps(PARSED, ensure_ascii=False), "[]"]
    first = await client.post(
        "/receipts", files={"file": ("a.png", PNG, "image/png")}, headers=anna.headers
    )
    other = PNG + b"\x00"  # другой файл
    second = await client.post(
        "/receipts", files={"file": ("b.png", other, "image/png")}, headers=anna.headers
    )
    assert first.status_code == 201 and second.status_code == 429


# --- ограничения ответов модели и токены ---


async def test_requests_limit_answer_length_and_photo_detail(
    client: httpx.AsyncClient, anna: Account, llm: FakeLLM
):
    photo = (
        await client.post(
            "/photos", files={"file": ("a.png", PNG, "image/png")}, headers=anna.headers
        )
    ).json()["id"]
    llm.replies = [CLASSIFIED]
    await client.post(
        "/issues/classify",
        json={"text": "яма на дороге", "photo_ids": [photo]},
        headers=anna.headers,
    )
    assert llm.max_tokens == [300]
    image = llm.calls[0][1]["content"][1]["image_url"]
    assert image["detail"] == "low"


async def test_openai_client_sends_limit_and_counts_tokens():
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen.update(json.loads(request.content))
        reply = {"choices": [{"message": {"content": "ок"}}], "usage": {"total_tokens": 42}}
        return httpx.Response(200, json=reply)

    client = OpenAICompatibleClient("https://llm.test", "k", "m", 5.0, httpx.MockTransport(handler))
    await client.complete([{"role": "user", "content": "привет"}], max_tokens=100)
    assert seen["max_tokens"] == 100 and tokens_today() == 42
    seen.clear()
    modern = OpenAICompatibleClient(
        "https://llm.test", "k", "m", 5.0, httpx.MockTransport(handler),
        max_tokens_param="max_completion_tokens",
    )  # fmt: skip
    await modern.complete([{"role": "user", "content": "привет"}], max_tokens=7)
    assert seen["max_completion_tokens"] == 7 and "max_tokens" not in seen


async def test_ollama_client_counts_tokens_and_limits_answer():
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen.update(json.loads(request.content))
        return httpx.Response(
            200, json={"message": {"content": "ок"}, "prompt_eval_count": 10, "eval_count": 5}
        )

    client = OllamaClient("http://ollama.test", "q", 5.0, httpx.MockTransport(handler))
    await client.complete([{"role": "user", "content": "привет"}], max_tokens=64)
    assert seen["options"]["num_predict"] == 64 and tokens_today() == 15


async def test_meta_shows_tokens_of_the_day(client: httpx.AsyncClient):
    from app.llm.tokens import add_tokens

    add_tokens(120)
    assert (await client.get("/meta")).json()["llm_tokens_today"] == 120


# --- входы по IP ---


async def test_logins_are_limited_per_ip(client: httpx.AsyncClient, settings):
    settings(LOGINS_PER_IP_PER_HOUR=3)
    for _ in range(3):
        response = await client.post("/auth/telegram/widget", json=sign_widget(now_fields()))
        assert response.status_code == 200
    blocked = await client.post("/auth/telegram/widget", json=sign_widget(now_fields()))
    assert blocked.status_code == 429 and blocked.json()["code"] == "login_rate_limited"
    assert int(blocked.headers["Retry-After"]) > 0


async def test_failed_logins_count_too(client: httpx.AsyncClient, settings):
    settings(LOGINS_PER_IP_PER_HOUR=2)
    for _ in range(2):
        forged = await client.post("/auth/telegram/webapp", json={"init_data": "hash=00"})
        assert forged.status_code == 401
    assert (await client.post("/auth/telegram/webapp", json={"init_data": "x"})).status_code == 429


async def test_other_users_logins_unaffected_by_quota(client: httpx.AsyncClient):
    assert (await dev_login(client, 777)).id
