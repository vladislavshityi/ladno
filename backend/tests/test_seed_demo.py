from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.collectives.models import CollectiveIssue, CollectiveMember
from app.modules.issues.models import Issue
from app.modules.ratings import service as ratings
from app.modules.users.models import User
from app.seed_demo import clear_demo, seed_demo


async def _counts(session: AsyncSession) -> tuple[int, int]:
    users = await session.scalar(select(func.count()).select_from(User))
    issues = await session.scalar(select(func.count()).select_from(Issue))
    return users, issues


async def test_seed_demo_is_idempotent_and_keeps_real_users(session: AsyncSession):
    real = User(telegram_id=4242)
    session.add(real)
    await session.commit()

    first = await seed_demo(session)
    counts = await _counts(session)
    second = await seed_demo(session)

    assert first == second and counts == await _counts(session)
    assert 150 <= counts[1] <= 250
    assert await session.get(User, real.id) is not None


async def test_seed_demo_gives_companies_different_scores(session: AsyncSession):
    await seed_demo(session)
    ratings.reset_cache()

    scores = [r.score for r in await ratings.all_ratings(session) if r.score is not None]

    assert len(scores) >= 8
    assert min(scores) <= 35 and max(scores) >= 75


async def test_clear_removes_only_demo_data(session: AsyncSession):
    real = User(telegram_id=4243)
    session.add(real)
    await session.commit()
    await seed_demo(session)

    await clear_demo(session)

    assert await _counts(session) == (1, 0)
    assert await session.scalar(select(func.count()).select_from(CollectiveIssue)) == 0


async def test_seed_demo_creates_collectives_of_three_to_six_residents(session: AsyncSession):
    await seed_demo(session)

    sizes = (
        await session.scalars(
            select(func.count())
            .select_from(CollectiveMember)
            .group_by(CollectiveMember.collective_id)
        )
    ).all()
    assert len(sizes) == 3 and all(3 <= size <= 6 for size in sizes)
    linked = await session.scalar(
        select(func.count()).select_from(Issue).where(Issue.collective_id.is_not(None))
    )
    assert linked == sum(sizes)
