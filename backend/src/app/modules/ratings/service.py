"""Рейтинг управляющих компаний: как они отвечают на обращения жителей.

В рейтинг идут поданные обращения с адресатом «управляющая компания» по домам, у которых УК
известна. Эскалации (обращение, у которого есть дочернее на следующую ступень) снижают балл УК.
Расчёт — один агрегирующий SQL; результат хранится в памяти процесса несколько минут.
"""

import time
from collections import defaultdict
from collections.abc import Awaitable, Callable
from typing import Literal

from sqlalchemy import and_, exists, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from app.core.errors import NotFound
from app.modules.houses.models import House, ManagementCompany
from app.modules.issues.models import ACTIVE_STATUSES, Issue, IssueStatus
from app.modules.issues.rules import MANAGING_COMPANY
from app.modules.ratings.schemas import (
    BreakdownItem,
    CompanyDetail,
    CompanyRating,
    HouseLoad,
)
from app.modules.ratings.scoring import MIN_ISSUES, CompanyStats, compute_score

CACHE_SECONDS = 300
TOP_CATEGORIES = 3
MONTHS = 6
HOUSES_LIMIT = 20

SortKey = Literal["score", "issues", "overdue"]

_cache: dict[object, tuple[float, object]] = {}


def reset_cache() -> None:
    _cache.clear()


async def _cached[T](key: object, load: Callable[[], Awaitable[T]]) -> T:
    hit = _cache.get(key)
    if hit and time.monotonic() - hit[0] < CACHE_SECONDS:
        return hit[1]  # type: ignore[return-value]
    value = await load()
    _cache[key] = (time.monotonic(), value)
    return value


def _rated_issues():
    """Обращения, которые учитываются в рейтинге: по одной строке на обращение с УК дома."""
    child = aliased(Issue)
    has_child = exists().where(child.parent_issue_id == Issue.id)
    return (
        select(
            House.management_company_id.label("company_id"),
            House.id.label("house_id"),
            House.address,
            Issue.category,
            Issue.status,
            Issue.deadline_at,
            Issue.answered_at,
            func.coalesce(Issue.submitted_at, Issue.created_at).label("at"),
            or_(Issue.escalation_level > 0, has_child).label("escalated"),
        )
        .join(House, Issue.house_id == House.id)
        .where(
            Issue.status != IssueStatus.DRAFT,
            Issue.addressee_key == MANAGING_COMPANY,
            House.management_company_id.is_not(None),
        )
        .subquery("rated")
    )


async def _stats(session: AsyncSession) -> dict[int, CompanyStats]:
    rated = _rated_issues()
    c = rated.c
    overdue = and_(c.status.in_(ACTIVE_STATUSES), c.deadline_at < func.now())
    on_time = and_(
        c.answered_at.is_not(None), or_(c.deadline_at.is_(None), c.answered_at <= c.deadline_at)
    )
    stmt = select(
        c.company_id,
        func.count().label("issues_total"),
        func.count().filter(c.status == IssueStatus.RESOLVED).label("resolved"),
        func.count().filter(c.status == IssueStatus.REJECTED).label("rejected"),
        func.count().filter(c.status == IssueStatus.NO_RESPONSE).label("no_response"),
        func.count().filter(overdue).label("overdue_now"),
        func.count().filter(on_time).label("on_time"),
        func.count().filter(c.escalated).label("escalated"),
    ).group_by(c.company_id)
    return {
        r.company_id: CompanyStats(
            r.issues_total, r.resolved, r.rejected, r.no_response, r.overdue_now, r.on_time,
            r.escalated,
        )
        for r in await session.execute(stmt)
    }  # fmt: skip


async def _top_categories(session: AsyncSession) -> dict[int, list[str]]:
    c = _rated_issues().c
    total = func.count()
    stmt = select(c.company_id, c.category, total).group_by(c.company_id, c.category)
    stmt = stmt.order_by(c.company_id, total.desc(), c.category)
    top: dict[int, list[str]] = defaultdict(list)
    for company_id, category, _ in await session.execute(stmt):
        if len(top[company_id]) < TOP_CATEGORIES:
            top[company_id].append(category)
    return top


async def _load_ratings(session: AsyncSession) -> list[CompanyRating]:
    stats = await _stats(session)
    top = await _top_categories(session)
    rows = await session.execute(
        select(
            ManagementCompany.id,
            ManagementCompany.name,
            func.count(House.id),
            func.array_remove(func.array_agg(House.district.distinct()), None),
        )
        .join(House, House.management_company_id == ManagementCompany.id)
        .where(ManagementCompany.id.in_(list(stats)))
        .group_by(ManagementCompany.id)
    )
    return [
        CompanyRating(
            id=company_id,
            name=name,
            score=compute_score(s := stats[company_id]),
            issues_total=s.issues_total,
            resolved_share=s.resolved_share,
            on_time_share=s.on_time_share,
            escalated_share=s.escalated_share,
            overdue_now=s.overdue_now,
            houses_count=houses_count,
            districts=sorted(districts),
            top_categories=top[company_id],
        )
        for company_id, name, houses_count, districts in rows
    ]


async def all_ratings(session: AsyncSession) -> list[CompanyRating]:
    return await _cached("ratings", lambda: _load_ratings(session))


async def scores(session: AsyncSession) -> dict[int, int | None]:
    """Баллы всех УК, у которых есть обращения: для подписи на карте."""
    return {r.id: r.score for r in await all_ratings(session)}


def _sort_key(sort: SortKey):
    def key(rating: CompanyRating) -> tuple:
        # УК без балла («мало данных») всегда в конце.
        no_score = rating.score is None
        if sort == "issues":
            return (no_score, -rating.issues_total, rating.name)
        if sort == "overdue":
            return (no_score, -rating.overdue_now, rating.name)
        return (no_score, -(rating.score or 0), -rating.issues_total, rating.name)

    return key


async def list_ratings(
    session: AsyncSession, district: str | None, sort: SortKey
) -> list[CompanyRating]:
    ratings = await all_ratings(session)
    if district:
        ratings = [r for r in ratings if district in r.districts]
    return sorted(ratings, key=_sort_key(sort))


async def _grouped(
    session: AsyncSession, company_id: int, key, order, limit: int | None = None
) -> list[BreakdownItem]:
    """Разбивка обращений УК; группы меньше MIN_ISSUES не выводятся: по ним можно узнать автора."""
    rated = _rated_issues()
    c = rated.c
    group = key(c)
    stmt = (
        select(group, func.count(), func.count().filter(c.status == IssueStatus.RESOLVED))
        .where(c.company_id == company_id)
        .group_by(group)
        .having(func.count() >= MIN_ISSUES)
        .order_by(*order(group))
        .limit(limit)
    )
    return [
        BreakdownItem(key=k, issues_total=t, resolved=r) for k, t, r in await session.execute(stmt)
    ]


async def _houses(session: AsyncSession, company_id: int) -> list[HouseLoad]:
    c = _rated_issues().c
    active = func.count().filter(c.status.in_(ACTIVE_STATUSES))
    stmt = (
        select(c.house_id, c.address, func.count(), active)
        .where(c.company_id == company_id)
        .group_by(c.house_id, c.address)
        .having(func.count() >= MIN_ISSUES)
        .order_by(active.desc(), c.address)
        .limit(HOUSES_LIMIT)
    )
    return [
        HouseLoad(house_id=h, address=a, issues_total=t, active=n)
        for h, a, t, n in await session.execute(stmt)
    ]


async def _load_detail(session: AsyncSession, company_id: int) -> CompanyDetail:
    rating = next((r for r in await all_ratings(session) if r.id == company_id), None)
    company = await session.get(ManagementCompany, company_id)
    if rating is None or company is None:
        raise NotFound("По этой УК пока нет обращений")
    by_month = await _grouped(
        session, company_id, lambda c: func.to_char(c.at, "YYYY-MM"), lambda g: [g.desc()], MONTHS
    )
    return CompanyDetail(
        **rating.model_dump(),
        phones=company.phones,
        site=company.site,
        by_category=await _grouped(
            session, company_id, lambda c: c.category, lambda g: [func.count().desc(), g]
        ),
        by_month=by_month[::-1],
        houses=await _houses(session, company_id),
    )


async def company_detail(session: AsyncSession, company_id: int) -> CompanyDetail:
    return await _cached(("detail", company_id), lambda: _load_detail(session, company_id))
