"""Тексты обращения: абзац «суть» (LLM с проверками, иначе шаблон) и черновики из шаблонов."""

import json
import re
from datetime import date
from typing import Any

from app.core.config import get_settings
from app.core.errors import AppError
from app.core.region import get_region
from app.core.templates import render
from app.core.text import numbers_are_supported, truncate
from app.llm.client import LLMClient
from app.llm.fallbacks import record_fallback
from app.modules.issues.rules import HOUSING_INSPECTION, MANAGING_COMPANY
from app.modules.issues.schemas import Addressee, Draft, RouteResult

SUMMARY_MAX_CHARS = 600
OTHER_CATEGORY = "other"
_SUMMARY_PROMPT = (
    "Перескажи проблему жителя деловым языком от первого лица, 2–4 предложения. Главный источник — "
    "поле description (слова жителя), category и answers уточняют его. Адресат в поле addressee "
    "только для сведения: не называй его и не пиши, в какую организацию обращаешься. "
    "Не добавляй чисел, имён, мест и сведений, которых нет в фактах. Не пиши просьб и требований: "
    "они будут в письме отдельно."
)
_UK_APPEAL = re.compile(r"\b(?:в|к)\s+(?:управляющ\w+\s+(?:компани|организаци)\w+|УК\b)", re.I)


def category_title(category: str) -> str:
    found = get_region().category(category)
    return found["title"] if found else category


def readable_answers(category: str, answers: dict[str, str]) -> dict[str, str]:
    """{id вопроса: значение} -> {текст вопроса: подпись ответа}; неизвестное остаётся как есть."""
    questions = {q["id"]: q for q in get_region().rules.get(category, {}).get("questions") or []}
    result = {}
    for question_id, value in answers.items():
        question = questions.get(question_id)
        labels = {o["value"]: o["label"] for o in question["options"]} if question else {}
        result[question["text"] if question else question_id] = labels.get(value, value)
    return result


def _template_summary(title: str, answers: dict[str, str], description: str) -> str:
    text = render("letters/issue_summary.j2", title=title, answers=answers, description=description)
    return " ".join(text.split())


def summary_fits(text: str, addressee_key: str) -> bool:
    """Текст не должен адресовать обращение в УК, если адресат — другая организация."""
    return addressee_key == MANAGING_COMPANY or not _UK_APPEAL.search(text)


async def _llm_summary(
    llm: LLMClient, title: str, answers: dict[str, str], addressee: Addressee, description: str
) -> str | None:
    if not description and not answers:
        return None  # пересказывать нечего: модель начнёт сочинять
    facts = json.dumps(
        {
            "description": description,
            "category": title,
            "answers": answers,
            "addressee": addressee.name,
        },
        ensure_ascii=False,
    )
    messages = [{"role": "system", "content": _SUMMARY_PROMPT}, {"role": "user", "content": facts}]
    try:
        text = (await llm.complete(messages)).strip()
    except AppError:
        record_fallback("summary")
        return None
    valid = 0 < len(text) <= SUMMARY_MAX_CHARS and numbers_are_supported(text, facts)
    if valid and summary_fits(text, addressee.key):
        return text
    record_fallback("summary", "текст модели не прошёл проверки")
    return None


async def build_summary(
    llm: LLMClient | None,
    category: str,
    answers: dict[str, str],
    addressee: Addressee,
    description: str = "",
) -> str:
    """Текст модели берём, только если прошёл проверки; иначе шаблонный."""
    title, readable = category_title(category), readable_answers(category, answers)
    description = description.strip()
    text = await _llm_summary(llm, title, readable, addressee, description) if llm else None
    template_title = "" if category == OTHER_CATEGORY else title  # «Другое» ничего не поясняет
    return text or _template_summary(template_title, readable, description)


def _draft(template: str, context: dict[str, Any]) -> Draft:
    short = " ".join(render("letters/issue_pos_short.j2", **context).split())
    return Draft(
        full=render(template, **context),
        pos_short=truncate(short, get_settings().pos_text_limit),
    )


def _context(
    summary: str,
    route: RouteResult,
    address: str | None,
    location_details: str | None,
    photos_count: int,
    applicant: str,
    previous: dict[str, Any] | None,
) -> dict[str, Any]:
    return {
        "summary": summary,
        "address": address,
        "location_details": location_details,
        "addressee_name": route.addressee.name,
        "basis": route.basis,
        "fix_deadline": route.fix_deadline,
        "response_deadline": route.response_deadline,
        "photos_count": photos_count,
        "date": date.today().strftime("%d.%m.%Y"),
        "applicant": applicant,
        "previous": previous,
    }


def build_draft(
    summary: str,
    route: RouteResult,
    address: str | None,
    location_details: str | None,
    photos_count: int,
    applicant: str,
) -> Draft:
    context = _context(summary, route, address, location_details, photos_count, applicant, None)
    return _draft("letters/issue_letter.j2", context)


def build_escalation_draft(
    summary: str,
    route: RouteResult,
    address: str | None,
    location_details: str | None,
    photos_count: int,
    applicant: str,
    previous: dict[str, Any],
) -> Draft:
    """previous: addressee_name, ref (номер первого обращения) и date (дата его подачи)."""
    context = _context(summary, route, address, location_details, photos_count, applicant, previous)
    inspection = route.addressee.key == HOUSING_INSPECTION
    template = (
        "letters/escalation_housing_inspection.j2" if inspection else "letters/issue_letter.j2"
    )
    return _draft(template, context)
