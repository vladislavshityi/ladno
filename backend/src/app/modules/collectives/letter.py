"""Коллективное письмо: адресат, нормы и сроки — из маршрута исходного обращения, текст — шаблон."""

import uuid
from datetime import date, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.templates import render
from app.core.text import plural
from app.modules.collectives.models import CollectiveIssue, CollectiveMember
from app.modules.collectives.schemas import CollectiveLetter
from app.modules.houses.models import House
from app.modules.issues import letter_pdf
from app.modules.issues.models import Issue
from app.modules.issues.schemas import RouteResult
from app.modules.users.models import User

RESIDENTS = ("житель", "жителя", "жителей")


def _residents(count: int) -> str:
    return f"{count} {plural(count, *RESIDENTS)}"


def _applicant(user: User) -> str | None:
    """«Иванов И. И., кв. 12»; None, если жилец не указал ни того ни другого."""
    parts = [user.full_name, f"кв. {user.apartment}" if user.apartment else None]
    return ", ".join(p for p in parts if p) or None


def _day(moment: datetime) -> str:
    return moment.strftime("%d.%m.%Y")


async def _members(
    session: AsyncSession, collective_id: uuid.UUID
) -> list[tuple[CollectiveMember, User]]:
    stmt = (
        select(CollectiveMember, User)
        .join(User, User.id == CollectiveMember.user_id)
        .where(CollectiveMember.collective_id == collective_id)
        .order_by(CollectiveMember.joined_at)
    )
    return [(m, u) for m, u in (await session.execute(stmt)).all()]


async def _consenting_users(session: AsyncSession, collective_id: uuid.UUID) -> set[uuid.UUID]:
    """Участники, разрешившие показать свои данные в письме: только их фото прикладываются."""
    return {m.user_id for m, _ in await _members(session, collective_id) if m.consent_letter}


async def member_issues(session: AsyncSession, collective_id: uuid.UUID) -> list[Issue]:
    stmt = select(Issue).where(Issue.collective_id == collective_id).order_by(Issue.created_at)
    return list((await session.scalars(stmt)).all())


async def build_letter(session: AsyncSession, collective: CollectiveIssue) -> CollectiveLetter:
    members = await _members(session, collective.id)
    issues = await member_issues(session, collective.id)
    consenting = await _consenting_users(session, collective.id)
    # Письмо строится по обращению инициатора; если его удалили, по самому раннему из оставшихся.
    base = next((i for i in issues if i.id == collective.initiator_issue_id), issues[0])
    route = RouteResult.model_validate(base.route)
    # Данные в письме — только у тех, кто согласился; остальные входят числом.
    applicants = [a for m, u in members if m.consent_letter and (a := _applicant(u))]
    anonymous = len(members) - len(applicants)
    days = [i.submitted_at or i.created_at for i in issues]
    text = render(
        "letters/collective_letter.j2",
        addressee_name=route.addressee.name,
        address=(await session.get(House, collective.house_id)).address,
        summary=base.summary,
        members_phrase=_residents(len(members)),
        first_date=_day(min(days)),
        last_date=_day(max(days)),
        applicants=applicants,
        anonymous_count=anonymous,
        anonymous_phrase=_residents(anonymous),
        basis=route.basis,
        fix_deadline=route.fix_deadline,
        response_deadline=route.response_deadline,
        photos_count=sum(len(i.photo_ids) for i in issues if i.user_id in consenting),
        date=date.today().strftime("%d.%m.%Y"),
    )
    return CollectiveLetter(text=text, members_count=len(members))


async def render_pdf(session: AsyncSession, collective: CollectiveIssue, text: str) -> bytes:
    """PDF письма с фото участников, которые согласились на раскрытие своих данных в письме."""
    consenting = await _consenting_users(session, collective.id)
    attachments = []
    for issue in await member_issues(session, collective.id):
        if issue.user_id in consenting:
            attachments += await letter_pdf.load_photos(session, issue)
    return await letter_pdf.render_pdf(text, attachments)
