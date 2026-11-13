"""Тексты обращения: абзац «суть» (LLM с проверками, иначе шаблон) и черновики из шаблонов."""

import json
import logging
import re
from datetime import date
from typing import Any

from app.core.config import get_settings
from app.core.errors import AppError
from app.core.region import get_region
from app.core.templates import render
from app.core.text import numbers_are_supported, truncate
from app.llm.client import LLMClient
from app.modules.issues.rules import HOUSING_INSPECTION, MANAGING_COMPANY
from app.modules.issues.schemas import Addressee, Draft, RouteResult

log = logging.getLogger(__name__)

SUMMARY_MAX_CHARS = 600
_SUMMARY_PROMPT = (
    "Напиши один абзац сути обращения жителя по фактам ниже. Адресат указан в поле addressee "
    "только для сведения: не называй его и не пиши, в какую организацию обращаешься. "
    "Не добавляй чисел, имён и сведений, которых нет в фактах."
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


def _template_summary(title: str, answers: dict[str, str]) -> str:
    return " ".join(render("letters/issue_summary.j2", title=title, answers=answers).split())


def summary_fits(text: str, addressee_key: str) -> bool:
    """Текст не должен адресовать обращение в УК, если адресат — другая организация."""
    return addressee_key == MANAGING_COMPANY or not _UK_APPEAL.search(text)


async def _llm_summary(
    llm: LLMClient, title: str, answers: dict[str, str], addressee: Addressee
) -> str | None:
    facts = json.dumps(
        {"category": title, "answers": answers, "addressee": addressee.name}, ensure_ascii=False
    )
    messages = [{"role": "system", "content": _SUMMARY_PROMPT}, {"role": "user", "content": facts}]
    try:
        text = (await llm.complete(messages)).strip()
    except AppError:
        log.warning("Модель не написала суть обращения, берём шаблон")
        return None
    valid = 0 < len(text) <= SUMMARY_MAX_CHARS and numbers_are_supported(text, facts)
    return text if valid and summary_fits(text, addressee.key) else None


async def build_summary(
    llm: LLMClient | None, category: str, answers: dict[str, str], addressee: Addressee
) -> str:
    """Текст модели берём, только если прошёл проверки; иначе шаблонный."""
    title, readable = category_title(category), readable_answers(category, answers)
    text = await _llm_summary(llm, title, readable, addressee) if llm else None
    return text or _template_summary(title, readable)


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
