"""Контекст ассистента: справочник региона и данные самого пользователя. Без ФИО и контактов."""

from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.region import Region, get_region
from app.modules.issues.models import Issue
from app.modules.issues.schemas import RouteResult
from app.modules.receipts import diff
from app.modules.receipts.models import Receipt
from app.modules.receipts.service import receipt_data
from app.modules.users.models import User

MAX_ISSUES = 10
MAX_RECEIPTS = 2

SYSTEM_PROMPT = (
    "Ты помощник «Ладно» для жителей Владивостока. Помогаешь с двумя вещами: куда и как "
    "пожаловаться на проблему дома или двора и как читать квитанцию за ЖКХ. Отвечай по-русски, "
    "коротко и по делу. Опирайся только на переданные данные: адресатов, нормы и сроки называй "
    "из блока «Справочник региона», суммы бери из данных пользователя и сам не считай. Если "
    "чего-то в данных нет, скажи, что нужно уточнить, и предложи завести обращение в приложении. "
    "Вопросы про квитанцию и обращения жителя разбирай по блоку «Данные пользователя»: "
    "сравнивай начисления по строкам и называй, что выросло. Не проси ФИО, телефон и номер "
    "квартиры."
)


def _deadline(raw: dict[str, Any] | None) -> str:
    if not raw:
        return ""
    kind = "раб." if raw["type"] == "working" else "кал."
    return f"{raw['days']} {kind} дн. ({raw['source']})"


def _route_line(route: dict[str, Any], addressees: dict[str, Any]) -> str:
    name = addressees.get(route["addressee"], {}).get("name", route["addressee"])
    parts = [f"адресат: {name}"]
    if answer := _deadline(route.get("response_deadline")):
        parts.append(f"срок ответа: {answer}")
    if fix := _deadline(route.get("fix_deadline")):
        parts.append(f"срок устранения: {fix}")
    return "; ".join(parts)


def region_facts(region: Region) -> str:
    """Категории, адресаты и сроки из правил региона одним компактным текстом."""
    lines = []
    for category in region.categories:
        rules = region.rules.get(category["id"], {})
        routes = [*(rules.get("routes") or []), rules.get("default") or {}]
        variants = {_route_line(r, region.addressees) for r in routes if r.get("addressee")}
        lines.append(f"- {category['title']}: " + " | ".join(sorted(variants)))
    return "\n".join(lines)


def _issue_line(issue: Issue) -> str:
    route = RouteResult.model_validate(issue.route)
    line = f"- {issue.category}, статус {issue.status.value}, адресат {route.addressee.name}"
    if issue.deadline_at:
        line += f", ответ ждём до {issue.deadline_at:%d.%m.%Y}"
    return line


def _receipt_text(receipt: Receipt) -> str:
    lines = [f"  {x.service_name}: начислено {x.accrued} ₽" for x in receipt.lines]
    head = f"Квитанция за {receipt.period or 'неизвестный период'}, итого {receipt.total} ₽"
    return "\n".join([head, *lines])


def _changes_text(newer: Receipt, older: Receipt) -> str:
    """Разница между двумя квитанциями, посчитанная кодом: модели остаётся только пересказ."""
    result = diff.compare(receipt_data(older), receipt_data(newer))
    lines = [
        f"  {x.service_name}: {x.delta:+.2f} ₽" + (f" ({', '.join(x.flags)})" if x.flags else "")
        for x in result.lines
        if x.delta != 0
    ]
    head = f"Изменения {older.period} -> {newer.period}, итого {result.total_delta:+.2f} ₽"
    return "\n".join([head, *lines])


async def user_facts(session: AsyncSession, user: User) -> str:
    stmt = select(Issue).where(Issue.user_id == user.id).order_by(Issue.created_at.desc())
    issues = (await session.scalars(stmt.limit(MAX_ISSUES))).all()
    receipts = (
        await session.scalars(
            select(Receipt)
            .where(Receipt.user_id == user.id)
            .order_by(Receipt.period.desc().nulls_last(), Receipt.created_at.desc())
            .limit(MAX_RECEIPTS)
        )
    ).all()
    sections = []
    if user.management_company:
        sections.append(f"УК пользователя: {user.management_company.name}")
    if issues:
        sections.append("Обращения пользователя:\n" + "\n".join(_issue_line(i) for i in issues))
    sections += [_receipt_text(r) for r in receipts]
    if len(receipts) == MAX_RECEIPTS:
        sections.append(_changes_text(*receipts))
    return "\n".join(sections) or "Данных пользователя пока нет."


async def build_system_prompt(session: AsyncSession, user: User) -> str:
    facts = await user_facts(session, user)
    return (
        f"{SYSTEM_PROMPT}\n\nСправочник региона:\n{region_facts(get_region())}\n\n"
        f"Данные пользователя:\n{facts}"
    )
