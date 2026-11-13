import uuid
from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import utcnow
from app.core.errors import NotFound
from app.modules.bot.schemas import BotIssue, Reminder
from app.modules.issues.deadlines import is_overdue
from app.modules.issues.drafts import category_title
from app.modules.issues.models import ACTIVE_STATUSES, Issue
from app.modules.issues.schemas import RouteResult
from app.modules.users.models import User

REMIND_BEFORE = timedelta(days=1)
LIST_LIMIT = 10


def _addressee_name(issue: Issue) -> str:
    return RouteResult.model_validate(issue.route).addressee.name


async def list_user_issues(session: AsyncSession, telegram_id: int) -> list[BotIssue]:
    user = await session.scalar(select(User).where(User.telegram_id == telegram_id))
    if user is None:
        raise NotFound("Пользователь не найден")
    stmt = select(Issue).where(Issue.user_id == user.id).order_by(Issue.created_at.desc())
    now = utcnow()
    return [
        BotIssue(
            id=i.id,
            category_title=category_title(i.category),
            status=i.status,
            addressee_name=_addressee_name(i),
            deadline_at=i.deadline_at,
            is_overdue=is_overdue(now, i.deadline_at, i.status),
        )
        for i in (await session.scalars(stmt.limit(LIST_LIMIT))).all()
    ]


async def due_reminders(session: AsyncSession) -> list[Reminder]:
    """Поданные обращения с истекающим или истёкшим сроком ответа, без напоминания."""
    now = utcnow()
    stmt = (
        select(Issue, User.telegram_id)
        .join(User, User.id == Issue.user_id)
        .where(
            Issue.status.in_(ACTIVE_STATUSES),
            Issue.deadline_at.is_not(None),
            Issue.deadline_at <= now + REMIND_BEFORE,
            Issue.reminder_sent_at.is_(None),
        )
        .order_by(Issue.deadline_at)
    )
    return [
        Reminder(
            issue_id=issue.id,
            telegram_id=telegram_id,
            category_title=category_title(issue.category),
            addressee_name=_addressee_name(issue),
            deadline_at=issue.deadline_at,
            is_overdue=issue.deadline_at < now,
        )
        for issue, telegram_id in (await session.execute(stmt)).all()
    ]


async def mark_reminder_sent(session: AsyncSession, issue_id: uuid.UUID) -> None:
    issue = await session.get(Issue, issue_id)
    if issue is None:
        raise NotFound("Обращение не найдено")
    issue.reminder_sent_at = utcnow()
    await session.commit()
