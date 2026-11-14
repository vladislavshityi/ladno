import json
from collections.abc import AsyncIterator

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from app.core.deps import CurrentUser, LLMDep, SessionDep, quota
from app.core.errors import AppError, ServiceUnavailable
from app.core.quota import grant_llm
from app.core.rate_limit import LLMRateLimit
from app.llm.client import LLMClient
from app.modules.assistant.context import build_system_prompt
from app.modules.assistant.schemas import ChatRequest

MAX_TOKENS = 700

router = APIRouter(prefix="/assistant", tags=["assistant"])


def _event(payload: dict, name: str | None = None) -> str:
    head = f"event: {name}\n" if name else ""
    return f"{head}data: {json.dumps(payload, ensure_ascii=False)}\n\n"


async def _stream_events(llm: LLMClient, messages: list[dict]) -> AsyncIterator[str]:
    try:
        async for delta in llm.stream(messages, max_tokens=MAX_TOKENS):
            yield _event({"delta": delta})
    except AppError as exc:
        yield _event({"detail": exc.detail, "code": exc.code}, name="error")
    yield "data: [DONE]\n\n"


@router.post(
    "/chat",
    response_class=StreamingResponse,
    dependencies=[LLMRateLimit, quota("assistant")],
    responses={200: {"content": {"text/event-stream": {}}, "description": "Поток SSE"}},
)
async def chat(
    data: ChatRequest, user: CurrentUser, session: SessionDep, llm: LLMDep
) -> StreamingResponse:
    """Ответ ассистента потоком SSE: `data: {"delta": "..."}`, в конце `data: [DONE]`.

    При сбое модели посреди ответа приходит событие `error`. История диалога не хранится.
    """
    llm = await grant_llm(session, llm)
    if llm is None:
        raise ServiceUnavailable("Ассистент сейчас недоступен", "llm_unavailable")
    system = {
        "role": "system",
        "content": await build_system_prompt(session, user, data.issue_ids, data.receipt_ids),
    }
    messages = [system, *(m.model_dump() for m in data.messages)]
    return StreamingResponse(_stream_events(llm, messages), media_type="text/event-stream")
