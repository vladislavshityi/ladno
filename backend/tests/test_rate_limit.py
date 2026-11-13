import httpx
import pytest

from app.core.config import get_settings
from tests.conftest import Account


async def test_llm_endpoints_are_rate_limited_per_user(
    client: httpx.AsyncClient, anna: Account, boris: Account, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setenv("LLM_REQUESTS_PER_MINUTE", "2")
    get_settings.cache_clear()
    try:
        body = {"text": "не горит свет"}
        for _ in range(2):
            assert (
                await client.post("/issues/classify", json=body, headers=anna.headers)
            ).status_code == 200
        limited = await client.post("/issues/classify", json=body, headers=anna.headers)
        assert limited.status_code == 429 and limited.json()["code"] == "rate_limited"
        chat = {"messages": [{"role": "user", "content": "привет"}]}
        assert (
            await client.post("/assistant/chat", json=chat, headers=anna.headers)
        ).status_code == 429
        upload = await client.post(
            "/receipts",
            files={"file": ("a.png", b"\x89PNG\r\n\x1a\n", "image/png")},
            headers=anna.headers,
        )
        assert upload.status_code == 429
        assert (
            await client.post("/issues/classify", json=body, headers=boris.headers)
        ).status_code == 200
    finally:
        monkeypatch.undo()
        get_settings.cache_clear()
