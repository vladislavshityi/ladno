from pydantic import TypeAdapter, ValidationError

from app.llm.client import LLMClient, Message


def strip_fence(text: str) -> str:
    """Модели любят оборачивать JSON в ```json ... ```."""
    text = text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[-1].rsplit("```", 1)[0]
    return text.strip()


async def ask_json[T](
    llm: LLMClient,
    messages: list[Message],
    adapter: TypeAdapter[T],
    model: str | None = None,
    max_tokens: int | None = None,
) -> T:
    """Ответ модели как JSON по схеме; при невалидном ответе один повтор с текстом ошибки."""
    text = await llm.complete(messages, json_mode=True, model=model, max_tokens=max_tokens)
    try:
        return adapter.validate_json(strip_fence(text))
    except ValidationError as exc:
        hint = {"role": "user", "content": f"Прошлый ответ не подошёл: {exc}. Верни только JSON."}
        retry = await llm.complete(
            [*messages, hint], json_mode=True, model=model, max_tokens=max_tokens
        )
        return adapter.validate_json(strip_fence(retry))
