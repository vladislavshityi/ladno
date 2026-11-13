import json

import httpx
import pytest
from pydantic import TypeAdapter

from app.core.config import get_settings
from app.core.errors import BadGateway, GatewayTimeout, ServiceUnavailable
from app.llm.client import OllamaClient, OpenAICompatibleClient, get_llm, vision_model
from app.llm.structured import ask_json, strip_fence

MESSAGES = [{"role": "user", "content": "привет"}]


def openai(handler) -> OpenAICompatibleClient:
    return OpenAICompatibleClient(
        "https://llm.test/v1/", "key-1", "model-x", 5.0, httpx.MockTransport(handler)
    )


def ollama(handler) -> OllamaClient:
    return OllamaClient("http://ollama.test", "qwen", 5.0, httpx.MockTransport(handler))


async def test_openai_complete_sends_auth_and_reads_content():
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen.update(url=str(request.url), auth=request.headers["Authorization"],
                    body=json.loads(request.content))  # fmt: skip
        return httpx.Response(200, json={"choices": [{"message": {"content": "ответ"}}]})

    assert await openai(handler).complete(MESSAGES, json_mode=True) == "ответ"
    assert seen["url"] == "https://llm.test/v1/chat/completions" and seen["auth"] == "Bearer key-1"
    assert seen["body"] == {"model": "model-x", "messages": MESSAGES, "temperature": 0}


async def test_openai_stream_parses_sse():
    sse = (
        'data: {"choices":[{"delta":{"role":"assistant"}}]}\n\n'
        'data: {"choices":[{"delta":{"content":"При"}}]}\n\n'
        'data: {"choices":[{"delta":{"content":"вет"}}]}\n\n'
        "data: [DONE]\n\n"
    )

    def handler(request: httpx.Request) -> httpx.Response:
        assert json.loads(request.content)["stream"] is True
        return httpx.Response(200, content=sse.encode())

    chunks = [c async for c in openai(handler).stream(MESSAGES)]
    assert chunks == ["При", "вет"]


async def test_errors_are_mapped_to_app_errors():
    def failing(status: int):
        return lambda request: httpx.Response(status, json={"error": "boom"})

    with pytest.raises(BadGateway):
        await openai(failing(500)).complete(MESSAGES)
    with pytest.raises(BadGateway):
        _ = [c async for c in openai(failing(429)).stream(MESSAGES)]

    def timeout(request: httpx.Request):
        raise httpx.ReadTimeout("slow", request=request)

    def refused(request: httpx.Request):
        raise httpx.ConnectError("no route", request=request)

    with pytest.raises(GatewayTimeout):
        await openai(timeout).complete(MESSAGES)
    with pytest.raises(ServiceUnavailable):
        await openai(refused).complete(MESSAGES)
    with pytest.raises(ServiceUnavailable):
        _ = [c async for c in ollama(refused).stream(MESSAGES)]


async def test_ollama_complete_json_mode_and_images():
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen.update(url=str(request.url), body=json.loads(request.content))
        return httpx.Response(200, json={"message": {"content": "{}"}})

    parts = [
        {"type": "text", "text": "что на фото"},
        {"type": "image_url", "image_url": {"url": "data:image/png;base64,QUJD"}},
    ]
    messages = [{"role": "user", "content": parts}]
    assert await ollama(handler).complete(messages, json_mode=True) == "{}"
    assert seen["url"] == "http://ollama.test/api/chat"
    assert seen["body"]["format"] == "json" and seen["body"]["stream"] is False
    assert seen["body"]["messages"] == [
        {"role": "user", "content": "что на фото", "images": ["QUJD"]}
    ]


async def test_ollama_stream_reads_ndjson():
    lines = [{"message": {"content": "а"}}, {"message": {"content": "б"}}, {"done": True}]
    body = "\n".join(json.dumps(x) for x in lines)

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=body.encode())

    assert [c async for c in ollama(handler).stream(MESSAGES)] == ["а", "б"]


async def test_ask_json_retries_once_with_error_hint():
    calls = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(json.loads(request.content)["messages"])
        text = "не json" if len(calls) == 1 else '```json\n{"a": 1}\n```'
        return httpx.Response(200, json={"choices": [{"message": {"content": text}}]})

    result = await ask_json(openai(handler), MESSAGES, TypeAdapter(dict[str, int]))
    assert result == {"a": 1} and len(calls) == 2
    assert "Прошлый ответ не подошёл" in calls[1][-1]["content"]


def test_strip_fence():
    assert strip_fence('```json\n{"a": 1}\n```') == '{"a": 1}'
    assert strip_fence(' {"a": 1} ') == '{"a": 1}'


def configure(monkeypatch: pytest.MonkeyPatch, **env: str) -> None:
    for key, value in env.items():
        monkeypatch.setenv(key, value)
    get_settings.cache_clear()


def test_get_llm_by_provider(monkeypatch: pytest.MonkeyPatch):
    try:
        assert get_llm() is None
        configure(monkeypatch, LLM_PROVIDER="ollama")
        assert isinstance(get_llm(), OllamaClient)
        configure(monkeypatch, LLM_PROVIDER="openai")
        assert get_llm() is None  # нет ключа и адреса: модель не настроена
        configure(monkeypatch, LLM_BASE_URL="https://x/v1", LLM_API_KEY="k", LLM_MODEL="m")
        assert isinstance(get_llm(), OpenAICompatibleClient)
    finally:
        monkeypatch.undo()
        get_settings.cache_clear()


def test_vision_model_by_provider(monkeypatch: pytest.MonkeyPatch):
    env = {"LLM_VISION_MODEL": "gpt-4o", "OLLAMA_VISION_MODEL": "llava"}
    for key, value in env.items():
        monkeypatch.setenv(key, value)
    try:
        for provider, expected in (("openai", "gpt-4o"), ("ollama", "llava")):
            monkeypatch.setenv("LLM_PROVIDER", provider)
            get_settings.cache_clear()
            assert vision_model() == expected
        monkeypatch.setenv("LLM_VISION_MODEL", "")
        monkeypatch.setenv("LLM_PROVIDER", "openai")
        get_settings.cache_clear()
        assert vision_model() is None  # пусто: используется обычная модель
    finally:
        get_settings.cache_clear()


async def test_complete_model_override_and_ollama_ignores_detail():
    seen = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(json.loads(request.content))
        return httpx.Response(
            200, json={"choices": [{"message": {"content": "{}"}}], "message": {"content": "{}"}}
        )

    part = {
        "type": "image_url",
        "image_url": {"url": "data:image/png;base64,QUJD", "detail": "high"},
    }
    messages = [{"role": "user", "content": [part]}]
    await openai(handler).complete(messages, model="gpt-4o")
    await ollama(handler).complete(messages, model="llava")
    assert seen[0]["model"] == "gpt-4o" and seen[1]["model"] == "llava"
    assert seen[1]["messages"][0]["images"] == ["QUJD"]
