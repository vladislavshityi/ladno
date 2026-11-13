import httpx
import pytest

from app.core.config import get_settings
from app.llm.fallbacks import llm_fallback_total
from tests.conftest import FakeLLM


async def test_meta_without_llm(client: httpx.AsyncClient):
    body = (await client.get("/meta")).json()
    assert body["llm"] is False and body["vision"] is False
    assert body["region"] == "vladivostok" and body["demo_data"] is False


async def test_meta_with_llm_provider(client: httpx.AsyncClient, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("LLM_PROVIDER", "openai")
    monkeypatch.setenv("LLM_BASE_URL", "http://llm.test")
    monkeypatch.setenv("LLM_API_KEY", "key")
    monkeypatch.setenv("LLM_MODEL", "gpt")
    get_settings.cache_clear()
    try:
        body = (await client.get("/meta")).json()
    finally:
        monkeypatch.undo()
        get_settings.cache_clear()
    assert body["llm"] is True and body["vision"] is True


async def test_meta_ollama_vision_follows_models(
    client: httpx.AsyncClient, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setenv("LLM_PROVIDER", "ollama")
    monkeypatch.setenv("OLLAMA_MODEL", "")
    monkeypatch.setenv("OLLAMA_VISION_MODEL", "")
    get_settings.cache_clear()
    try:
        assert (await client.get("/meta")).json()["vision"] is False
        monkeypatch.setenv("OLLAMA_VISION_MODEL", "llava")
        get_settings.cache_clear()
        assert (await client.get("/meta")).json()["vision"] is True
    finally:
        monkeypatch.undo()
        get_settings.cache_clear()


async def test_meta_counts_llm_fallbacks(client: httpx.AsyncClient, llm: FakeLLM):
    from app.core.errors import GatewayTimeout
    from tests.conftest import dev_login

    llm_fallback_total.clear()
    llm.error = GatewayTimeout("долго", "llm_timeout")
    who = await dev_login(client, 2001)
    await client.post("/issues/classify", json={"text": "плохо"}, headers=who.headers)
    assert (await client.get("/meta")).json()["llm_fallbacks"] == {"classify": 1}
    llm_fallback_total.clear()


async def test_faq_is_public_and_has_norms(client: httpx.AsyncClient):
    faq = (await client.get("/faq")).json()
    assert 8 <= len(faq) <= 12
    assert all(item["question"] and item["answer"] for item in faq)
    assert any(item["basis"] and item["basis"][0]["verified"] is False for item in faq)
