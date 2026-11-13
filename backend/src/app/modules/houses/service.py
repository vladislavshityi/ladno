import csv
from dataclasses import dataclass
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.errors import NotFound
from app.modules.houses import address_search
from app.modules.houses.models import House, ManagementCompany
from app.modules.houses.schemas import AddressSuggestion

SEARCH_LIMIT = 10
COMPANIES_LIMIT = 20
SEED_CHUNK = 1000


@dataclass(frozen=True)
class IndexedHouse:
    id: int
    address: str
    lat: float | None
    lon: float | None
    key: address_search.HouseKey


_index: list[IndexedHouse] | None = None


def reset_index() -> None:
    global _index
    _index = None


async def _house_index(session: AsyncSession) -> list[IndexedHouse]:
    """Разобранные адреса всех домов: справочник не меняется между перезапусками."""
    global _index
    if _index is None:
        rows = await session.execute(
            select(House.id, House.address, House.lat, House.lon).order_by(House.id)
        )
        _index = [
            IndexedHouse(r.id, r.address, r.lat, r.lon, address_search.parse_address(r.address))
            for r in rows
        ]
    return _index


async def search_addresses(session: AsyncSession, q: str) -> list[AddressSuggestion]:
    index = await _house_index(session)
    hits = address_search.search(q, [(h.address, h.key) for h in index], SEARCH_LIMIT)
    return [
        AddressSuggestion(house_id=h.id, address=h.address, lat=h.lat, lon=h.lon)
        for h in (index[i] for i in hits)
    ]


async def get_house(session: AsyncSession, house_id: int) -> House:
    house = await session.get(House, house_id)
    if house is None:
        raise NotFound("Дом не найден")
    return house


async def list_companies(session: AsyncSession, q: str | None) -> list[ManagementCompany]:
    stmt = select(ManagementCompany).order_by(ManagementCompany.name).limit(COMPANIES_LIMIT)
    if q and q.strip():
        stmt = stmt.where(ManagementCompany.name.icontains(q.strip(), autoescape=True))
    return list((await session.scalars(stmt)).all())


async def get_company(session: AsyncSession, company_id: int) -> ManagementCompany:
    company = await session.get(ManagementCompany, company_id)
    if company is None:
        raise NotFound("Управляющая компания не найдена")
    return company


def _read_csv(name: str) -> list[dict[str, str]]:
    path: Path = get_settings().region_dir / f"{name}.csv"
    with path.open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def _blank_to_none(value: str | None) -> str | None:
    return (value or "").strip() or None


def _company_row(row: dict[str, str]) -> dict:
    phones = [p.strip() for p in (row["phones"] or "").split(";") if p.strip()]
    return {
        "id": int(row["id"]),
        "inn": _blank_to_none(row["inn"]),
        "name": row["name"],
        "phones": phones,
        "email": _blank_to_none(row["email"]),
        "emergency_phone": _blank_to_none(row["emergency_phone"]),
        "site": _blank_to_none(row["site"]),
    }


def _house_row(row: dict[str, str]) -> dict:
    lat, lon, company = (_blank_to_none(row[k]) for k in ("lat", "lon", "management_company_id"))
    return {
        "fias_id": row["fias_id"],
        "address": row["address"],
        "lat": float(lat) if lat else None,
        "lon": float(lon) if lon else None,
        "district": _blank_to_none(row["district"]),
        "management_company_id": int(company) if company else None,
    }


async def _upsert(session: AsyncSession, model: type, rows: list[dict], key: str) -> None:
    for start in range(0, len(rows), SEED_CHUNK):
        stmt = insert(model).values(rows[start : start + SEED_CHUNK])
        update = {c: stmt.excluded[c] for c in rows[0] if c != key}
        await session.execute(stmt.on_conflict_do_update(index_elements=[key], set_=update))


async def seed_houses(session: AsyncSession) -> tuple[int, int]:
    """Загружает УК и дома из CSV региона; повторный запуск обновляет записи по ключу."""
    companies = [_company_row(r) for r in _read_csv("management_companies")]
    houses = [_house_row(r) for r in _read_csv("houses")]
    await _upsert(session, ManagementCompany, companies, "id")
    await _upsert(session, House, houses, "fias_id")
    await session.commit()
    reset_index()
    return len(companies), len(houses)
