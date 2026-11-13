"""Классификация проблемы по тексту: LLM выбирает только категорию, аварии ищет код.

Без модели, при её сбое или сомнении категорию подбирают ключевые слова из справочника.
"""

import base64
import json

from pydantic import BaseModel, Field, TypeAdapter, ValidationError

from app.core.errors import AppError
from app.core.region import get_region
from app.llm.client import LLMClient, Message, vision_model
from app.llm.fallbacks import record_fallback
from app.llm.structured import ask_json
from app.modules.issues.keywords import match_category
from app.modules.issues.schemas import Classification, Contact, Emergency

# (содержимое, MIME-тип) загруженного фото
Image = tuple[bytes, str]

MIN_CONFIDENCE = 0.6
KEYWORD_CONFIDENCE = 0.6  # ключевые слова надёжны меньше модели: пользователь подтвердит выбор
DEFAULT_EMERGENCY_REASON = "Похоже на аварию"

_SYSTEM = (
    "Определи категорию проблемы ЖКХ по описанию и фото жителя. Ответь только JSON с полями: "
    "category (один из id списка или null), confidence (число от 0 до 1), is_emergency (true при "
    "угрозе жизни: газ, затопление, искрение, обрушение), summary (одна фраза о том, что видно или "
    "описано), clarification (если данных мало, один короткий вопрос, что уточнить; иначе пустая "
    "строка). Учитывай hint категорий: «Другое» — только если ничего не подходит. "
    "Не называй людей и номера квартир. Категории: "
)


class LLMAnswer(BaseModel):
    category: str | None = None
    confidence: float = Field(0.0, ge=0, le=1)
    is_emergency: bool = False
    summary: str = ""
    clarification: str = ""


_ANSWER = TypeAdapter(LLMAnswer)


def emergency_rule(text: str) -> dict | None:
    """Признаки аварии из справочника: проверяются кодом независимо от модели."""
    lowered = text.lower()
    for rule in get_region().classification.get("emergency", []):
        if any(word in lowered for word in rule["keywords"]):
            return rule
    return None


def _emergency_contacts(keys: list[str]) -> list[Contact]:
    """Телефоны экстренных служб берутся из справочника, а не из ответа модели."""
    addressees = get_region().addressees
    return [
        Contact.model_validate(channel)
        for key in keys
        for channel in addressees.get(key, {}).get("channels", [])
        if channel["type"] == "phone"
    ]


def _emergency(rule: dict | None, llm_flag: bool) -> Emergency | None:
    if rule is None and not llm_flag:
        return None
    if rule is None:
        keys = get_region().classification.get("emergency_addressees", [])
        return Emergency(reason=DEFAULT_EMERGENCY_REASON, contacts=_emergency_contacts(keys))
    return Emergency(
        reason=rule["reason"],
        advice=rule.get("advice"),
        contacts=_emergency_contacts(rule.get("addressees", [])),
    )


def _with_emergency(result: Classification, emergency: Emergency | None) -> Classification:
    return result.model_copy(update={"is_emergency": emergency is not None, "emergency": emergency})


def _user_message(text: str, images: list[Image]) -> Message:
    parts: list[dict] = [{"type": "text", "text": text or "Описания нет, смотри на фото."}]
    for data, content_type in images:
        data_uri = f"data:{content_type};base64,{base64.b64encode(data).decode()}"
        parts.append({"type": "image_url", "image_url": {"url": data_uri}})
    return {"role": "user", "content": parts}


async def _ask_llm(llm: LLMClient, text: str, images: list[Image]) -> LLMAnswer | None:
    categories = [
        {key: c[key] for key in ("id", "title", "hint") if key in c}
        for c in get_region().categories
    ]
    system = _SYSTEM + json.dumps(categories, ensure_ascii=False)
    messages = [{"role": "system", "content": system}, _user_message(text, images)]
    try:
        return await ask_json(llm, messages, _ANSWER, vision_model() if images else None)
    except (AppError, ValidationError, ValueError):
        record_fallback("classify")
        return None


def _by_keywords(text: str) -> Classification:
    keywords = {c["id"]: c.get("keywords", []) for c in get_region().categories}
    category = match_category(text, keywords)
    if category is None:
        return Classification(needs_manual_choice=True)
    return Classification(category=category, confidence=KEYWORD_CONFIDENCE)


async def classify(llm: LLMClient | None, text: str, images: list[Image]) -> Classification:
    """Ответ модели, если она уверена; иначе ключевые слова, а при сомнении — ручной выбор."""
    answer = await _ask_llm(llm, text, images) if llm else None
    emergency = _emergency(emergency_rule(text), bool(answer and answer.is_emergency))
    clarification = (answer.clarification.strip() if answer else "") or None
    known = answer is not None and get_region().category(answer.category or "") is not None
    if answer is not None and known and answer.confidence >= MIN_CONFIDENCE:
        result = Classification(
            category=answer.category,
            confidence=answer.confidence,
            summary=answer.summary,
            clarification=clarification,
        )
    else:
        if answer is not None:
            record_fallback("classify", "низкая уверенность")
        result = _by_keywords(text).model_copy(update={"clarification": clarification})
    return _with_emergency(result, emergency)
