"""Карта проблем: обращения, свёрнутые по домам. Ни текстов, ни фото, ни авторов."""

from datetime import timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.db import utcnow
from app.modules.houses.models import House
from app.modules.issues.models import ACTIVE_STATUSES, Issue, IssueStatus
from app.modules.map.schemas import MapCompany, MapPoint
from app.modules.ratings import service as ratings

# У обращения нет признака аварии (его определяет только классификатор текста и не сохраняется),
# поэтому аварийными считаются категории, где опасность в самой проблеме.
EMERGENCY_CATEGORIES = ("flooding", "open_manhole")


async def list_points(
    session: AsyncSession, category: str | None, days: int, active_only: bool
) -> list[MapPoint]:
    submitted = func.coalesce(Issue.submitted_at, Issue.created_at)
    is_active = Issue.status.in_(ACTIVE_STATUSES)
    stmt = (
        select(
            House,
            Issue.category,
            func.count().label("total"),
            func.count().filter(is_active).label("active"),
            func.count()
            .filter(is_active, Issue.category.in_(EMERGENCY_CATEGORIES))
            .label("urgent"),
        )
        .join(House, Issue.house_id == House.id)
        .where(
            Issue.status != IssueStatus.DRAFT,
            House.lat.is_not(None),
            House.lon.is_not(None),
            submitted >= utcnow() - timedelta(days=days),
        )
        .group_by(House.id, Issue.category)
        .order_by(House.id, Issue.category)
    )
    if category:
        stmt = stmt.where(Issue.category == category)
    if active_only:
        stmt = stmt.where(is_active)

    scores = await ratings.scores(session)
    points: dict[int, MapPoint] = {}
    for house, issue_category, total, active, urgent in await session.execute(stmt):
        point = points.get(house.id)
        if point is None:
            company = house.management_company
            point = points[house.id] = MapPoint(
                house_id=house.id,
                lat=house.lat,
                lon=house.lon,
                address=house.address,
                total=0,
                active=0,
                emergency=False,
                categories={},
                management_company=MapCompany(
                    id=company.id, name=company.name, score=scores.get(company.id)
                )
                if company
                else None,
            )
        point.total += total
        point.active += active
        point.emergency |= urgent > 0
        point.categories[issue_category] = total
    # Дом с одним-двумя обращениями выдал бы автора (дом, категория, срок), поэтому такие скрыты.
    threshold = get_settings().map_min_issues
    return [p for p in points.values() if p.total >= threshold]
