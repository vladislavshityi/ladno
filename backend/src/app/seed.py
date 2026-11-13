"""Идемпотентная загрузка справочников домов и УК: python -m app.seed."""

import asyncio

from app.core.db import get_engine, get_sessionmaker
from app.modules.houses.service import seed_houses


async def main() -> None:
    async with get_sessionmaker()() as session:
        companies, houses = await seed_houses(session)
    await get_engine().dispose()
    print(f"Загружено: УК {companies}, домов {houses}")


if __name__ == "__main__":
    asyncio.run(main())
