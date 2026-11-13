from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.houses.models import House, ManagementCompany
from app.modules.houses.service import seed_houses


async def test_seed_is_idempotent_and_loads_reference_data(session: AsyncSession):
    first = await seed_houses(session)
    second = await seed_houses(session)
    assert first == second == (408, 4057)
    assert await session.scalar(select(func.count()).select_from(House)) == 4057
    assert await session.scalar(select(func.count()).select_from(ManagementCompany)) == 408


async def test_seed_restores_changed_record(session: AsyncSession):
    house = await session.scalar(select(House).where(House.address.like("%Кутузова, д 5а")))
    house.address = "испорчено"
    await session.commit()
    await seed_houses(session)
    await session.refresh(house)
    assert house.address == "г Владивосток, ул Кутузова, д 5а"
