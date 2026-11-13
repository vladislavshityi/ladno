from datetime import timedelta

import httpx
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import utcnow
from app.modules.houses.models import House
from app.modules.issues.models import IssueStatus
from app.modules.users.models import User
from tests.issue_factory import add, make_issue


async def test_rating_counts_outcomes_and_escalations(
    client: httpx.AsyncClient, session: AsyncSession, resident: User, house: House
):
    answered = utcnow() - timedelta(days=35)
    stuck = make_issue(resident, house, IssueStatus.NO_RESPONSE)
    await add(
        session,
        make_issue(resident, house, IssueStatus.RESOLVED, answered_at=answered),
        make_issue(resident, house, IssueStatus.RESOLVED, answered_at=answered),
        stuck,
        make_issue(resident, house, IssueStatus.SUBMITTED),  # срок истёк
        make_issue(
            resident, house, IssueStatus.SUBMITTED, deadline_at=utcnow() + timedelta(days=3)
        ),
        make_issue(resident, house, IssueStatus.DRAFT),
    )
    # Жалоба в инспекцию: сама в рейтинг УК не входит, но у исходного обращения есть эскалация.
    await add(
        session,
        make_issue(
            resident, house, IssueStatus.RESOLVED, addressee_key="housing_inspection",
            parent_issue_id=stuck.id, escalation_level=1,
        ),
    )  # fmt: skip

    response = await client.get("/ratings/companies")

    assert response.status_code == 200
    (rating,) = response.json()
    assert rating["id"] == house.management_company_id
    assert rating["issues_total"] == 5
    assert rating["overdue_now"] == 1
    assert rating["resolved_share"] == pytest.approx(0.5)
    assert rating["on_time_share"] == pytest.approx(0.5)
    assert rating["escalated_share"] == pytest.approx(0.2)
    # 100 × (0.5 × 0.5 + 0.3 × 0.5 + 0.2 × 0.8)
    assert rating["score"] == 56
    assert rating["top_categories"] == ["elevator"]


async def test_company_with_few_issues_has_no_score(
    client: httpx.AsyncClient, session: AsyncSession, resident: User, house: House
):
    await add(
        session,
        make_issue(resident, house, IssueStatus.RESOLVED, answered_at=utcnow()),
        make_issue(resident, house, IssueStatus.DRAFT),
    )

    (rating,) = (await client.get("/ratings/companies")).json()

    assert rating["issues_total"] == 1
    assert rating["score"] is None


async def test_company_detail_hides_small_groups(
    client: httpx.AsyncClient, session: AsyncSession, resident: User, house: House
):
    await add(
        session,
        *[make_issue(resident, house, IssueStatus.SUBMITTED) for _ in range(3)],
        make_issue(resident, house, IssueStatus.SUBMITTED, category="garbage"),
    )

    response = await client.get(f"/ratings/companies/{house.management_company_id}")

    body = response.json()
    assert [i["key"] for i in body["by_category"]] == ["elevator"]
    assert len(body["by_month"]) == 1 and body["by_month"][0]["issues_total"] == 4
    assert body["houses"] == [
        {"house_id": house.id, "address": house.address, "issues_total": 4, "active": 4}
    ]


async def test_unknown_company_is_not_found(client: httpx.AsyncClient):
    assert (await client.get("/ratings/companies/1")).status_code == 404


async def test_list_filters_by_district_and_sorts_without_score_last(
    client: httpx.AsyncClient, session: AsyncSession, resident: User, house: House
):
    await add(session, make_issue(resident, house, IssueStatus.SUBMITTED))
    district = house.district

    found = (await client.get("/ratings/companies", params={"district": district})).json()
    other = (await client.get("/ratings/companies", params={"district": "нет такого"})).json()

    assert len(found) == 1 and other == []
    assert (await client.get("/ratings/companies", params={"sort": "overdue"})).status_code == 200
