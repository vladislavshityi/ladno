"""Демонстрационные обращения для рейтинга и карты: python -m app.seed_demo [--clear].

Синтетические жители (отрицательный telegram_id, без имён и контактов) подают обращения за
90 дней в самые крупные УК справочника. Повторный запуск пересоздаёт набор; настоящих
пользователей команда не трогает. Набор детерминирован.
"""

import argparse
import asyncio
import random
import uuid
from datetime import timedelta

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_engine, get_sessionmaker, utcnow
from app.modules.houses.models import House, ManagementCompany
from app.modules.issues import routing
from app.modules.issues.models import Issue, IssueStatus
from app.modules.issues.rules import MANAGING_COMPANY
from app.modules.issues.schemas import RouteResult
from app.modules.issues.service import mark_submitted
from app.modules.users.models import User

SEED = 20261114
DEMO_USERS = 40
HOUSES_PER_COMPANY = 7
PERIOD_DAYS = 90
# Категории, которые правила региона адресуют управляющей компании.
CATEGORIES = (
    "stairwell_lighting",
    "stairwell_cleaning",
    "elevator",
    "entrance_door",
    "flooding",
    "roof_leak",
    "utility_outage",
)

# (обращений, доля решённых, доля ответов в срок среди решённых, доля эскалаций среди нерешённых)
PROFILES = (
    (26, 0.90, 0.80, 0.10),
    (24, 0.85, 0.75, 0.15),
    (22, 0.75, 0.60, 0.25),
    (22, 0.60, 0.50, 0.35),
    (20, 0.50, 0.35, 0.50),
    (20, 0.35, 0.25, 0.55),
    (18, 0.32, 0.25, 0.55),
    (16, 0.25, 0.15, 0.60),
    (2, 0.50, 0.50, 0.00),  # мало обращений: балл не считается
)


def is_demo_user():
    return User.telegram_id < 0


async def clear_demo(session: AsyncSession) -> None:
    """Обращения синтетических жителей удаляются каскадом вместе с ними."""
    await session.execute(delete(User).where(is_demo_user()))
    await session.commit()


async def _largest_companies(session: AsyncSession) -> list[ManagementCompany]:
    houses = func.count(House.id)
    rows = await session.scalars(
        select(ManagementCompany)
        .join(House, House.management_company_id == ManagementCompany.id)
        .where(House.lat.is_not(None))
        .group_by(ManagementCompany.id)
        .order_by(houses.desc(), ManagementCompany.id)
        .limit(len(PROFILES))
    )
    return list(rows)


def _new_id(rng: random.Random) -> uuid.UUID:
    return uuid.UUID(int=rng.getrandbits(128), version=4)


def _issue(
    rng: random.Random, user_id: uuid.UUID, house_id: int, category: str, route: RouteResult
) -> Issue:
    return Issue(
        id=_new_id(rng),
        user_id=user_id,
        category=category,
        house_id=house_id,
        escalation_level=0,
        addressee_key=route.addressee.key,
        route=route.model_dump(mode="json"),
    )


def _escalation(rng: random.Random, parent: Issue, company: ManagementCompany) -> Issue | None:
    """Жалоба на следующую ступень: у исходного обращения появляется дочернее."""
    route = routing.build_escalated_route(RouteResult.model_validate(parent.route), company)
    if route is None:
        return None
    child = _issue(rng, parent.user_id, parent.house_id, parent.category, route)
    child.parent_issue_id = parent.id
    child.escalation_level = parent.escalation_level + 1
    mark_submitted(child, min(parent.deadline_at + timedelta(days=1), utcnow()))
    return child


def _company_issues(
    rng: random.Random,
    company: ManagementCompany,
    houses: list[House],
    users: list[User],
    profile: tuple[int, float, float, float],
) -> list[Issue]:
    count, resolved_share, on_time_share, escalated_share = profile
    now = utcnow()
    issues: list[Issue] = []
    for _ in range(count):
        category = rng.choice(CATEGORIES)
        route = routing.build_route(category, {}, False, company, None)
        if route.addressee.key != MANAGING_COMPANY or route.response_deadline is None:
            continue
        issue = _issue(rng, rng.choice(users).id, rng.choice(houses).id, category, route)
        # Срок ответа с запасом: старое обращение уже точно просрочено или закрыто.
        age = rng.uniform(route.response_deadline.days * 1.5 + 2, PERIOD_DAYS)

        if rng.random() < resolved_share:
            mark_submitted(issue, now - timedelta(days=age))
            issue.status = rng.choices([IssueStatus.RESOLVED, IssueStatus.REJECTED], [85, 15])[0]
            reply = rng.uniform(0.2, 0.95) if rng.random() < on_time_share else 1.4
            issue.answered_at = (
                issue.submitted_at + (issue.deadline_at - issue.submitted_at) * reply
            )
        elif rng.random() < 0.2:
            # Свежее обращение: срок ещё идёт, исходом не считается.
            mark_submitted(issue, now - timedelta(days=rng.uniform(0, 2)))
            issue.status = rng.choice([IssueStatus.SUBMITTED, IssueStatus.IN_PROGRESS])
        else:
            mark_submitted(issue, now - timedelta(days=age))
            issue.status = rng.choice(
                [IssueStatus.NO_RESPONSE, IssueStatus.IN_PROGRESS, IssueStatus.SUBMITTED]
            )
            issues.append(issue)
            if rng.random() < escalated_share and (child := _escalation(rng, issue, company)):
                issues.append(child)
            continue
        issues.append(issue)
    return issues


async def seed_demo(session: AsyncSession) -> tuple[int, int]:
    """Пересоздаёт демо-набор; возвращает число УК и обращений."""
    await clear_demo(session)
    rng = random.Random(SEED)
    users = [User(id=_new_id(rng), telegram_id=-1000 - i) for i in range(DEMO_USERS)]
    session.add_all(users)
    created = 0
    for company, profile in zip(await _largest_companies(session), PROFILES, strict=False):
        found = await session.scalars(
            select(House)
            .where(House.management_company_id == company.id, House.lat.is_not(None))
            .order_by(House.id)
        )
        candidates = list(found)
        houses = rng.sample(candidates, min(HOUSES_PER_COMPANY, len(candidates)))
        issues = _company_issues(rng, company, houses, users, profile)
        session.add_all(issues)
        created += len(issues)
    await session.commit()
    return len(PROFILES), created


async def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--clear", action="store_true", help="удалить демо-данные")
    args = parser.parse_args()
    async with get_sessionmaker()() as session:
        if args.clear:
            await clear_demo(session)
            print("Демо-данные удалены")
        else:
            companies, issues = await seed_demo(session)
            print(f"Демо-данные: УК {companies}, обращений {issues}")
    await get_engine().dispose()


if __name__ == "__main__":
    asyncio.run(main())
