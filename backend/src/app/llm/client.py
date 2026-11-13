import json
from collections.abc import AsyncIterator, Iterator
from contextlib import contextmanager
from typing import Any, Protocol

import httpx

from app.core.config import get_settings
from app.core.errors import BadGateway, GatewayTimeout, ServiceUnavailable

# Сообщение в формате OpenAI: content — строка или список частей (текст, изображение, файл).
Message = dict[str, Any]

UNAVAILABLE = "Языковая модель недоступна"


class LLMClient(Protocol):
    async def complete(self, messages: list[Message], *, json_mode: bool = False) -> str: ...

    def stream(self, messages: list[Message]) -> AsyncIterator[str]: ...


@contextmanager
def _map_transport_errors() -> Iterator[None]:
    try:
        yield
    except httpx.TimeoutException as exc:
        raise GatewayTimeout("Модель не ответила вовремя", "llm_timeout") from exc
    except httpx.HTTPError as exc:
        raise ServiceUnavailable(UNAVAILABLE, "llm_unavailable") from exc


def _raise_for_status(response: httpx.Response) -> None:
    if response.is_error:
        raise BadGateway(f"Модель вернула ошибку {response.status_code}", "llm_error")


class OpenAICompatibleClient:
    """Любой сервис с OpenAI-совместимым /chat/completions."""

    def __init__(
        self,
        base_url: str,
        api_key: str,
        model: str,
        timeout: float,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self.model = model
        self._http = {
            "base_url": base_url.rstrip("/"),
            "headers": {"Authorization": f"Bearer {api_key}"},
            "timeout": httpx.Timeout(timeout, connect=5.0),
            "transport": transport,
        }

    def _payload(self, messages: list[Message], **extra: Any) -> dict[str, Any]:
        return {"model": self.model, "messages": messages, **extra}

    async def complete(self, messages: list[Message], *, json_mode: bool = False) -> str:
        extra = {"temperature": 0} if json_mode else {}
        with _map_transport_errors():
            async with httpx.AsyncClient(**self._http) as client:
                response = await client.post(
                    "/chat/completions", json=self._payload(messages, **extra)
                )
        _raise_for_status(response)
        return response.json()["choices"][0]["message"]["content"] or ""

    async def stream(self, messages: list[Message]) -> AsyncIterator[str]:
        payload = self._payload(messages, stream=True)
        with _map_transport_errors():
            async with (
                httpx.AsyncClient(**self._http) as client,
                client.stream("POST", "/chat/completions", json=payload) as response,
            ):
                if response.is_error:
                    await response.aread()
                    _raise_for_status(response)
                async for line in response.aiter_lines():
                    if delta := _sse_delta(line):
                        yield delta


def _sse_delta(line: str) -> str:
    if not line.startswith("data:") or line.strip() == "data: [DONE]":
        return ""
    choices = json.loads(line.removeprefix("data:")).get("choices") or [{}]
    return choices[0].get("delta", {}).get("content") or ""


def _to_ollama(message: Message) -> Message:
    """Ollama принимает картинки отдельным полем base64, а не частями content."""
    content = message["content"]
    if isinstance(content, str):
        return message
    texts = [p["text"] for p in content if p.get("type") == "text"]
    images = [
        p["image_url"]["url"].split(",", 1)[-1] for p in content if p.get("type") == "image_url"
    ]
    return {"role": message["role"], "content": "\n".join(texts), "images": images}


class OllamaClient:
    """Локальная модель через Ollama (https://docs.ollama.com/api)."""

    def __init__(
        self,
        base_url: str,
        model: str,
        timeout: float,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self.model = model
        self._http = {
            "base_url": base_url.rstrip("/"),
            "timeout": httpx.Timeout(timeout, connect=5.0),
            "transport": transport,
        }

    def _payload(self, messages: list[Message], **extra: Any) -> dict[str, Any]:
        return {"model": self.model, "messages": [_to_ollama(m) for m in messages], **extra}

    async def complete(self, messages: list[Message], *, json_mode: bool = False) -> str:
        extra = {"format": "json", "options": {"temperature": 0}} if json_mode else {}
        payload = self._payload(messages, stream=False, **extra)
        with _map_transport_errors():
            async with httpx.AsyncClient(**self._http) as client:
                response = await client.post("/api/chat", json=payload)
        _raise_for_status(response)
        return response.json().get("message", {}).get("content", "")

    async def stream(self, messages: list[Message]) -> AsyncIterator[str]:
        with _map_transport_errors():
            async with (
                httpx.AsyncClient(**self._http) as client,
                client.stream("POST", "/api/chat", json=self._payload(messages)) as response,
            ):
                if response.is_error:
                    await response.aread()
                    _raise_for_status(response)
                async for line in response.aiter_lines():
                    if line and (content := json.loads(line).get("message", {}).get("content")):
                        yield content


def get_llm() -> LLMClient | None:
    """Клиент по LLM_PROVIDER; None — модель не настроена, и функции с ней деградируют."""
    s = get_settings()
    if s.llm_provider == "ollama":
        return OllamaClient(s.ollama_base_url, s.ollama_model, s.llm_timeout_seconds)
    if s.llm_provider == "openai" and s.llm_base_url and s.llm_api_key and s.llm_model:
        return OpenAICompatibleClient(
            s.llm_base_url, s.llm_api_key, s.llm_model, s.llm_timeout_seconds
        )
    return None
