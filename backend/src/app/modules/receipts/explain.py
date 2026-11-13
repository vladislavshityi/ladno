"""Объяснения строк и сравнения квитанций: текст модели проходит проверку чисел, иначе шаблон."""

import json
import logging

from pydantic import BaseModel, TypeAdapter, ValidationError

from app.core.errors import AppError
from app.core.region import get_region
from app.core.text import numbers_are_supported
from app.llm.client import LLMClient
from app.llm.structured import ask_json
from app.modules.receipts import texts
from app.modules.receipts.schemas import Compare, ReceiptLine
from app.modules.receipts.tariffs import service_note

log = logging.getLogger(__name__)

_LINES_PROMPT = (
    "Для каждой строки квитанции напиши одну короткую фразу простым языком: что это за услуга и "
    "от чего зависит сумма. Используй только числа из входных данных, ничего не пересчитывай. "
    'Верни только JSON-массив: [{"line_id": 1, "explanation": "..."}].'
)
_DIFF_PROMPT = (
    "Ты получил готовое сравнение двух квитанций ЖКХ. Объясни простым языком, почему изменилась "
    "сумма: 2-4 предложения. Используй только числа из входных данных, ничего не пересчитывай "
    "и не придумывай."
)


class _LineText(BaseModel):
    line_id: int
    explanation: str


_LINE_TEXTS = TypeAdapter(list[_LineText])


async def _llm_line_texts(llm: LLMClient, lines: list[ReceiptLine]) -> dict[int, str]:
    payload = json.dumps(
        [x.model_dump(mode="json", exclude={"explanation"}) for x in lines], ensure_ascii=False
    )
    messages = [
        {"role": "system", "content": _LINES_PROMPT},
        {"role": "user", "content": payload},
    ]
    try:
        return {x.line_id: x.explanation for x in await ask_json(llm, messages, _LINE_TEXTS)}
    except (AppError, ValidationError, ValueError):
        log.warning("Модель не объяснила строки квитанции, берём шаблоны")
        return {}


async def explain_lines(llm: LLMClient | None, lines: list[ReceiptLine]) -> dict[int, str]:
    """{id строки: объяснение}. Текст модели берём, только если все числа в нём есть в строке."""
    from_llm = await _llm_line_texts(llm, lines) if llm and lines else {}
    notes = get_region().tariffs
    result = {}
    for line in lines:
        fallback = texts.line_explanation(line, service_note(notes, line.service_code))
        candidate = from_llm.get(line.id)
        source = line.model_dump_json() + fallback
        supported = candidate and numbers_are_supported(candidate, source)
        result[line.id] = candidate if supported else fallback
    return result


async def explain_compare(llm: LLMClient | None, diff: Compare) -> str:
    fallback = texts.diff_explanation(diff)
    if llm is None:
        return fallback
    source = diff.model_dump_json()
    messages = [{"role": "system", "content": _DIFF_PROMPT}, {"role": "user", "content": source}]
    try:
        text = (await llm.complete(messages)).strip()
    except AppError:
        log.warning("Модель не объяснила сравнение, берём шаблон")
        return fallback
    return text if text and numbers_are_supported(text, source) else fallback
