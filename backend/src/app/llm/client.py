import json
from collections.abc import AsyncIterator, Iterator
from contextlib import contextmanager
from typing import Any, Protocol

import httpx

from app.core.config import get_settings
from app.core.errors import BadGateway, GatewayTimeout, ServiceUnavailable
from app.llm.tokens import add_tokens

# Сообщение в формате OpenAI: content — строка или список частей (текст, изображение, файл).
Message = dict[str, Any]

UNAVAILABLE = "Языковая модель недоступна"


class LLMClient(Protocol):
    async def complete(
        self,
        messages: list[Message],
        *,
        json_mode: bool = False,
        model: str | None = None,
        max_tokens: int | None = None,
    ) -> str: ...

    def stream(
        self, messages: list[Message], *, max_tokens: int | None = None
    ) -> AsyncIterator[str]: ...


@contextmanager
def _map_transport_errors() -> Iterator[None]:
    try:
        yield
    except httpx.TimeoutException as exc:
        raise GatewayTimeout("Модель не ответила вовремя", "llm_timeout") from exc
    except httpx.HTTPError as exc:
        raise ServiceUnavailable(UNAVAILABLE, "llm_unavailable") from exc


@contextmanager
def _unexpected_answer() -> Iterator[None]:
    """Тело ответа не того вида: для вызывающего это такая же ошибка модели."""
    try:
        yield
    except (ValueError, KeyError, IndexError, TypeError, AttributeError) as exc:
        raise BadGateway("Модель вернула неожиданный ответ", "llm_error") from exc


def _has_images(messages: list[Message]) -> bool:
    return any(
        isinstance(m["content"], list) and any(p.get("type") == "image_url" for p in m["content"])
        for m in messages
    )


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
        vision_timeout: float | None = None,
        max_tokens_param: str = "max_tokens",
    ) -> None:
        self.model = model
        self._max_tokens_param = max_tokens_param
        self._vision_timeout = httpx.Timeout(vision_timeout or timeout, connect=5.0)
        self._http = {
            "base_url": base_url.rstrip("/"),
            "headers": {"Authorization": f"Bearer {api_key}"},
            "timeout": httpx.Timeout(timeout, connect=5.0),
            "transport": transport,
        }

    def _timeout_for(self, messages: list[Message]) -> httpx.Timeout:
        """Разбор изображений идёт дольше текста, поэтому ждём его отдельно."""
        return self._vision_timeout if _has_images(messages) else self._http["timeout"]

    def _payload(
        self, messages: list[Message], model: str | None = None, **extra: Any
    ) -> dict[str, Any]:
        return {"model": model or self.model, "messages": messages, **extra}

    async def complete(
        self,
        messages: list[Message],
        *,
        json_mode: bool = False,
        model: str | None = None,
        max_tokens: int | None = None,
    ) -> str:
        extra = {"temperature": 0} if json_mode else {}
        if max_tokens:
            extra[self._max_tokens_param] = max_tokens
        with _map_transport_errors():
            async with httpx.AsyncClient(**self._http) as client:
                response = await client.post(
                    "/chat/completions",
                    json=self._payload(messages, model, **extra),
                    timeout=self._timeout_for(messages),
                )
        _raise_for_status(response)
        with _unexpected_answer():
            body = response.json()
            add_tokens(int((body.get("usage") or {}).get("total_tokens") or 0))
            return body["choices"][0]["message"]["content"] or ""

    async def stream(
        self, messages: list[Message], *, max_tokens: int | None = None
    ) -> AsyncIterator[str]:
        extra = {self._max_tokens_param: max_tokens} if max_tokens else {}
        payload = self._payload(messages, stream=True, **extra)
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
        vision_timeout: float | None = None,
    ) -> None:
        self.model = model
        self._vision_timeout = httpx.Timeout(vision_timeout or timeout, connect=5.0)
        self._http = {
            "base_url": base_url.rstrip("/"),
            "timeout": httpx.Timeout(timeout, connect=5.0),
            "transport": transport,
        }

    def _timeout_for(self, messages: list[Message]) -> httpx.Timeout:
        """Разбор изображений идёт дольше текста, поэтому ждём его отдельно."""
        return self._vision_timeout if _has_images(messages) else self._http["timeout"]

    def _payload(
        self, messages: list[Message], model: str | None = None, **extra: Any
    ) -> dict[str, Any]:
        return {
            "model": model or self.model,
            "messages": [_to_ollama(m) for m in messages],
            **extra,
        }

    async def complete(
        self,
        messages: list[Message],
        *,
        json_mode: bool = False,
        model: str | None = None,
        max_tokens: int | None = None,
    ) -> str:
        options = {"temperature": 0} if json_mode else {}
        if max_tokens:
            options["num_predict"] = max_tokens
        extra = {"format": "json"} if json_mode else {}
        payload = self._payload(messages, model, stream=False, options=options, **extra)
        with _map_transport_errors():
            async with httpx.AsyncClient(**self._http) as client:
                response = await client.post(
                    "/api/chat", json=payload, timeout=self._timeout_for(messages)
                )
        _raise_for_status(response)
        with _unexpected_answer():
            body = response.json()
            add_tokens(int(body.get("prompt_eval_count") or 0) + int(body.get("eval_count") or 0))
            return body.get("message", {}).get("content", "")

    async def stream(
        self, messages: list[Message], *, max_tokens: int | None = None
    ) -> AsyncIterator[str]:
        options = {"options": {"num_predict": max_tokens}} if max_tokens else {}
        with _map_transport_errors():
            async with (
                httpx.AsyncClient(**self._http) as client,
                client.stream(
                    "POST", "/api/chat", json=self._payload(messages, **options)
                ) as response,
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
        return OllamaClient(
            s.ollama_base_url,
            s.ollama_model,
            s.llm_timeout_seconds,
            vision_timeout=s.llm_vision_timeout_seconds,
        )
    if s.llm_provider == "openai" and s.llm_base_url and s.llm_api_key and s.llm_model:
        return OpenAICompatibleClient(
            s.llm_base_url,
            s.llm_api_key,
            s.llm_model,
            s.llm_timeout_seconds,
            vision_timeout=s.llm_vision_timeout_seconds,
            max_tokens_param=s.llm_max_tokens_param,
        )
    return None


def vision_available() -> bool:
    """Есть ли модель, понимающая изображения: в API-режиме та же, что для текста."""
    s = get_settings()
    if s.llm_provider == "ollama":
        return bool(s.ollama_vision_model or s.ollama_model)
    return get_llm() is not None


def vision_model() -> str | None:
    """Модель для разбора фото; None — та же, что для текста."""
    s = get_settings()
    return (s.ollama_vision_model if s.llm_provider == "ollama" else s.llm_vision_model) or None
