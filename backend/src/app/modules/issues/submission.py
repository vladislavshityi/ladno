"""Мягкая подача: ссылка на «Решаем вместе», текст, шаги и альтернативы.

Отправляет обращение сам человек.
"""

from app.core.config import get_settings
from app.core.region import get_region
from app.core.templates import render
from app.modules.issues.models import Issue
from app.modules.issues.rules import HOUSING_INSPECTION, MANAGING_COMPANY
from app.modules.issues.schemas import RouteResult, Submission, SubmissionAlternative

GIS_ZHKH_ADDRESSEES = {MANAGING_COMPANY, HOUSING_INSPECTION}


def _alternatives(route: RouteResult) -> list[SubmissionAlternative]:
    result = []
    if route.addressee.key in GIS_ZHKH_ADDRESSEES:
        result.append(
            SubmissionAlternative(
                channel="gis_zhkh_link",
                open_url=get_settings().gis_zhkh_url,
                label="Подать в ГИС ЖКХ",
            )
        )
    email = next((c for c in route.addressee.channels if c.type == "email"), None)
    if email:
        label = f"Скопировать текст и отправить на {email.value} ({route.addressee.name})"
        result.append(
            SubmissionAlternative(
                channel="email_copy", open_url=f"mailto:{email.value}", label=label
            )
        )
    return result


def build_submission(issue: Issue) -> Submission:
    settings = get_settings()
    category = get_region().category(issue.category) or {}
    hint = category.get("pos_hint")
    return Submission(
        text=issue.draft_pos_short,
        char_limit=settings.pos_text_limit,
        open_url=settings.pos_url,
        category_hint=hint,
        steps=render("submission/pos_steps.j2", hint=hint).splitlines(),
        alternatives=_alternatives(RouteResult.model_validate(issue.route)),
    )
