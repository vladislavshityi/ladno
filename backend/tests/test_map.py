import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.houses.models import House
from app.modules.issues.models import IssueStatus
from app.modules.users.models import User
from tests.issue_factory import add, make_issue


async def test_points_are_grouped_by_house_without_personal_data(
    client: httpx.AsyncClient, session: AsyncSession, resident: User, house: House
):
    await add(
        session,
        make_issue(resident, house, IssueStatus.SUBMITTED, category="elevator"),
        make_issue(resident, house, IssueStatus.RESOLVED, category="elevator"),
        make_issue(resident, house, IssueStatus.SUBMITTED, category="flooding"),
        make_issue(resident, house, IssueStatus.DRAFT),
        make_issue(resident, house, IssueStatus.SUBMITTED, house_id=None, custom_address="Тайга"),
    )

    response = await client.get("/map/points")

    (point,) = response.json()
    assert point["house_id"] == house.id
    assert (point["total"], point["active"], point["emergency"]) == (3, 2, True)
    assert point["categories"] == {"elevator": 2, "flooding": 1}
    assert point["management_company"]["id"] == house.management_company_id
    assert point["management_company"]["score"] == 37  # решено 1 из 3, в срок 0, эскалаций нет
    assert set(point) == {
        "house_id", "lat", "lon", "address", "total", "active", "emergency", "categories",
        "management_company",
    }  # fmt: skip


async def test_points_filters(
    client: httpx.AsyncClient, session: AsyncSession, resident: User, house: House
):
    await add(
        session,
        make_issue(resident, house, IssueStatus.RESOLVED, category="elevator"),
        make_issue(resident, house, IssueStatus.SUBMITTED, category="garbage"),
    )

    active = (await client.get("/map/points", params={"active": "true"})).json()
    elevators = (await client.get("/map/points", params={"category": "elevator"})).json()
    week = (await client.get("/map/points", params={"days": 7})).json()

    assert active[0]["categories"] == {"garbage": 1}
    assert elevators[0]["categories"] == {"elevator": 1}
    assert week == []  # обращения поданы 40 дней назад
    assert (await client.get("/map/points", params={"days": 0})).status_code == 422
