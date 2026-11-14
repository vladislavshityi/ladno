import uuid
from datetime import timedelta

import httpx
import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import utcnow
from app.modules.collectives.models import CollectiveIssue, CollectiveMember
from app.modules.houses.models import House
from app.modules.issues.models import Issue, IssueStatus
from app.modules.users.models import User
from tests.conftest import PNG, Account, dev_login

ELEVATOR = {"category": "elevator", "answers": {}}


async def another_house(session: AsyncSession, house: House) -> House:
    found = await session.scalars(select(House).where(House.id != house.id).limit(1))
    return found.one()


async def report(
    client: httpx.AsyncClient, who: Account, house: House, category: str = "elevator", **body
) -> str:
    payload = {"category": category, "house_id": house.id, "description": "Лифт не работает"}
    response = await client.post("/issues", json=payload | body, headers=who.headers)
    assert response.status_code == 201, response.text
    return response.json()["id"]


async def age(session: AsyncSession, issue_id: str, days: int, status: IssueStatus | None = None):
    issue = await session.get(Issue, uuid.UUID(issue_id))
    issue.created_at = utcnow() - timedelta(days=days)
    if status:
        issue.status = status
    await session.flush()


async def similar(client: httpx.AsyncClient, who: Account, house: House, category="elevator"):
    params = {"house_id": house.id, "category": category}
    response = await client.get("/issues/similar", params=params, headers=who.headers)
    assert response.status_code == 200, response.text
    return response.json()


async def join(client: httpx.AsyncClient, who: Account, issue_id: str, **body):
    payload = {"issue_id": issue_id, "consent": True} | body
    return await client.post("/collectives/join", json=payload, headers=who.headers)


async def neighbour(client: httpx.AsyncClient, number: int) -> Account:
    return await dev_login(client, 2000 + number)


# --- поиск похожих ---


async def test_similar_counts_other_residents_not_myself(
    client: httpx.AsyncClient, session: AsyncSession, anna: Account, boris: Account, house: House
):
    await report(client, anna, house)
    assert await similar(client, anna, house) == {"count": 0, "collective_id": None}
    assert (await similar(client, boris, house))["count"] == 1
    await report(client, anna, house, location_details="подъезд 2")  # тот же житель: не считается
    assert (await similar(client, boris, house))["count"] == 1


async def test_similar_ignores_other_category_house_and_closed_issues(
    client: httpx.AsyncClient, session: AsyncSession, anna: Account, boris: Account, house: House
):
    elsewhere = await another_house(session, house)
    await report(client, anna, house, "stairwell_cleaning")
    await report(client, anna, elsewhere)
    for status in (IssueStatus.RESOLVED, IssueStatus.REJECTED):
        await age(session, await report(client, anna, house), 1, status)
    assert (await similar(client, boris, house))["count"] == 0


@pytest.mark.parametrize("status", ["draft", "submitted", "in_progress", "no_response"])
async def test_similar_counts_active_statuses(
    client: httpx.AsyncClient, session: AsyncSession, anna: Account, boris: Account, house: House,
    status: str,
):  # fmt: skip
    await age(session, await report(client, anna, house), 1, IssueStatus(status))
    assert (await similar(client, boris, house))["count"] == 1


async def test_similar_window_is_thirty_days(
    client: httpx.AsyncClient, session: AsyncSession, anna: Account, boris: Account, house: House
):
    recent, old = await report(client, anna, house), await report(client, boris, house)
    carol = await neighbour(client, 1)
    await age(session, recent, 29)
    assert (await similar(client, carol, house))["count"] == 2
    await age(session, old, 31)
    assert (await similar(client, carol, house))["count"] == 1


async def test_similar_counts_synthetic_residents(
    client: httpx.AsyncClient, session: AsyncSession, anna: Account, house: House, resident: User
):
    session.add(Issue(user_id=resident.id, category="elevator", house_id=house.id,
                      addressee_key="managing_company", route={}))  # fmt: skip
    await session.flush()
    assert (await similar(client, anna, house))["count"] == 1


# --- присоединение ---


async def test_join_creates_collective_around_earliest_issue(
    client: httpx.AsyncClient, session: AsyncSession, anna: Account, boris: Account, house: House
):
    first = await report(client, anna, house)
    await age(session, first, 3)
    mine = await report(client, boris, house)

    response = await join(client, boris, mine, consent_letter=True)
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["members_count"] == 2 and body["status"] == "open"
    assert body["my_issue_id"] == mine and body["consent_letter"] is True
    assert body["category"] == "elevator" and body["address"] == house.address

    for who, issue_id in ((anna, first), (boris, mine)):
        issue = (await client.get(f"/issues/{issue_id}", headers=who.headers)).json()
        assert issue["collective_id"] == body["id"]
    found = await similar(client, await neighbour(client, 2), house)
    assert found == {"count": 2, "collective_id": body["id"]}


async def test_third_resident_joins_existing_collective(
    client: httpx.AsyncClient, anna: Account, boris: Account, house: House
):
    await report(client, anna, house)
    collective_id = (await join(client, boris, await report(client, boris, house))).json()["id"]
    carol = await neighbour(client, 3)
    response = await join(client, carol, await report(client, carol, house))
    assert response.json()["id"] == collective_id and response.json()["members_count"] == 3


async def test_join_twice_is_conflict(
    client: httpx.AsyncClient, anna: Account, boris: Account, house: House
):
    await report(client, anna, house)
    mine = await report(client, boris, house)
    assert (await join(client, boris, mine)).status_code == 201
    again = await join(client, boris, mine)
    assert again.status_code == 409 and again.json()["code"] == "already_joined"
    second = await report(client, boris, house)
    assert (await join(client, boris, second)).status_code == 409


async def test_join_requires_explicit_consent(
    client: httpx.AsyncClient, anna: Account, boris: Account, house: House
):
    await report(client, anna, house)
    mine = await report(client, boris, house)
    assert (await join(client, boris, mine, consent=False)).status_code == 422
    no_field = {"issue_id": mine}
    assert (
        await client.post("/collectives/join", json=no_field, headers=boris.headers)
    ).status_code == 422
    assert (await similar(client, anna, house))["collective_id"] is None


async def test_join_with_foreign_issue_is_not_found(
    client: httpx.AsyncClient, anna: Account, boris: Account, house: House
):
    theirs = await report(client, anna, house)
    assert (await join(client, boris, theirs)).status_code == 404
    assert (await join(client, boris, str(uuid.uuid4()))).status_code == 404


async def test_join_without_similar_issues_or_directory_house(
    client: httpx.AsyncClient, anna: Account, house: House
):
    alone = await report(client, anna, house)
    response = await join(client, anna, alone)
    assert response.status_code == 409 and response.json()["code"] == "no_similar_issues"
    custom = await client.post("/issues", json=ELEVATOR | {"custom_address": "Где-то, 1"},
                               headers=anna.headers)  # fmt: skip
    assert (await join(client, anna, custom.json()["id"])).status_code == 422


# --- приватность ---


async def test_collective_shows_only_member_count_to_members(
    client: httpx.AsyncClient, session: AsyncSession, anna: Account, boris: Account, house: House
):
    for who in (anna, boris):
        user = await session.get(User, uuid.UUID(who.id))
        user.full_name, user.apartment = f"Секретов {who.telegram_id}", "кв-7431"
    await session.flush()
    await report(client, anna, house)
    created = (await join(client, boris, await report(client, boris, house))).json()

    body = (await client.get(f"/collectives/{created['id']}", headers=anna.headers)).json()
    assert body["members_count"] == 2
    assert "Секретов" not in str(body) and "7431" not in str(body)

    stranger = await neighbour(client, 4)
    for url in ("", "/letter.pdf"):
        response = await client.get(f"/collectives/{created['id']}{url}", headers=stranger.headers)
        assert response.status_code == 404
    letter = await client.post(f"/collectives/{created['id']}/letter", headers=stranger.headers)
    assert letter.status_code == 404


# --- письмо ---


async def make_collective(
    client: httpx.AsyncClient, session: AsyncSession, house: House, members: list[Account],
    consenting: set[int] = frozenset(),
) -> str:  # fmt: skip
    collective_id = ""
    for number, who in enumerate(members):
        user = await session.get(User, uuid.UUID(who.id))
        user.full_name, user.apartment = f"Жилец{number} Тестов", str(10 + number)
        await session.flush()
        issue_id = await report(client, who, house)
        await age(session, issue_id, len(members) - number)
        if number:
            response = await join(client, who, issue_id, consent_letter=number in consenting)
            collective_id = response.json()["id"]
    return collective_id


async def letter_text(client: httpx.AsyncClient, who: Account, collective_id: str) -> str:
    response = await client.post(f"/collectives/{collective_id}/letter", headers=who.headers)
    assert response.status_code == 200, response.text
    return response.json()["text"]


async def test_letter_needs_two_members(
    client: httpx.AsyncClient, session: AsyncSession, anna: Account, house: House
):
    issue_id = await report(client, anna, house)
    collective = CollectiveIssue(house_id=house.id, category="elevator")
    session.add(collective)
    await session.flush()
    session.add(CollectiveMember(collective_id=collective.id, user_id=uuid.UUID(anna.id),
                                 issue_id=uuid.UUID(issue_id)))  # fmt: skip
    await session.flush()
    for call in (
        client.post(f"/collectives/{collective.id}/letter", headers=anna.headers),
        client.get(f"/collectives/{collective.id}/letter.pdf", headers=anna.headers),
        client.post(f"/collectives/{collective.id}/submit", headers=anna.headers),
    ):
        response = await call
        assert response.status_code == 409 and response.json()["code"] == "not_enough_members"


async def test_letter_with_two_members_names_only_consenting(
    client: httpx.AsyncClient, session: AsyncSession, anna: Account, boris: Account, house: House
):
    collective_id = await make_collective(client, session, house, [anna, boris], consenting={1})
    text = await letter_text(client, boris, collective_id)
    assert "Кому: " in text and house.address in text
    assert "2 жителя" in text and "Жилец1 Тестов, кв. 11" in text
    assert "Жилец0" not in text and "Без указания данных в письме: ещё 1 житель." in text
    assert "Коллективное обращение" in text and "Приложения: нет." in text


async def test_letter_without_any_consent_has_no_personal_data(
    client: httpx.AsyncClient, session: AsyncSession, anna: Account, boris: Account, house: House
):
    collective_id = await make_collective(client, session, house, [anna, boris])
    text = await letter_text(client, anna, collective_id)
    assert "Тестов" not in text and "Заявители:" not in text
    assert "Без указания данных в письме: 2 жителя." in text


async def test_letter_with_ten_members_uses_declension_and_dates(
    client: httpx.AsyncClient, session: AsyncSession, house: House
):
    residents = [await neighbour(client, 10 + n) for n in range(10)]
    collective_id = await make_collective(
        client, session, house, residents, consenting=set(range(1, 6))
    )
    text = await letter_text(client, residents[0], collective_id)
    assert "10 жителей" in text and "Жилец5 Тестов, кв. 15" in text and "Жилец6" not in text
    assert "Без указания данных в письме: ещё 5 жителей." in text
    first = (utcnow() - timedelta(days=10)).strftime("%d.%m.%Y")
    last = (utcnow() - timedelta(days=1)).strftime("%d.%m.%Y")
    assert f"поданы {first}, последнее — {last}" in text


async def test_letter_takes_addressee_and_deadlines_from_route(
    client: httpx.AsyncClient, session: AsyncSession, anna: Account, boris: Account, house: House
):
    collective_id = await make_collective(client, session, house, [anna, boris])
    issue = (await client.get("/issues", headers=anna.headers)).json()[0]
    route = issue["route"]
    text = await letter_text(client, anna, collective_id)
    assert route["addressee"]["name"] in text
    if route["response_deadline"]:
        assert route["response_deadline"]["source"] in text


async def test_letter_includes_photos_only_of_consenting_members(
    client: httpx.AsyncClient, session: AsyncSession, anna: Account, boris: Account, house: House
):
    """Фото соседа видны в письме и PDF, только если он разрешил показать свои данные."""
    photo_ids = []
    for who in (anna, boris):
        upload = await client.post("/photos", files={"file": ("a.png", PNG, "image/png")},
                                   headers=who.headers)  # fmt: skip
        photo_ids.append(upload.json()["id"])
    await report(client, anna, house, photo_ids=photo_ids[:1])
    boris_issue = await report(client, boris, house, photo_ids=photo_ids[1:])
    collective_id = (await join(client, boris, boris_issue, consent_letter=True)).json()["id"]

    text = await letter_text(client, anna, collective_id)
    assert "фотографии жителей, 1 шт." in text  # Анна ещё не согласилась, Борис согласился
    pdf = await client.get(f"/collectives/{collective_id}/letter.pdf", headers=anna.headers)
    assert pdf.status_code == 200 and pdf.content.startswith(b"%PDF")
    assert pdf.content.count(b"/Subtype /Image") == 1

    patch = {"consent_letter": True}
    await client.patch(f"/collectives/{collective_id}/membership", json=patch, headers=anna.headers)
    assert "фотографии жителей, 2 шт." in await letter_text(client, anna, collective_id)


# --- согласие, подача, бот ---


async def test_membership_consent_can_be_changed(
    client: httpx.AsyncClient, session: AsyncSession, anna: Account, boris: Account, house: House
):
    collective_id = await make_collective(client, session, house, [anna, boris])
    patch = {"consent_letter": True}
    response = await client.patch(f"/collectives/{collective_id}/membership", json=patch,
                                  headers=anna.headers)  # fmt: skip
    assert response.json()["consent_letter"] is True
    assert "Жилец0 Тестов" in await letter_text(client, boris, collective_id)


async def test_submit_starts_deadlines_of_member_drafts(
    client: httpx.AsyncClient, session: AsyncSession, anna: Account, boris: Account, house: House
):
    collective_id = await make_collective(client, session, house, [anna, boris])
    response = await client.post(f"/collectives/{collective_id}/submit", headers=boris.headers)
    assert response.status_code == 200 and response.json()["status"] == "submitted"
    for who in (anna, boris):
        issue = (await client.get("/issues", headers=who.headers)).json()[0]
        assert issue["status"] == "submitted" and issue["deadline_at"]
    again = await client.post(f"/collectives/{collective_id}/submit", headers=boris.headers)
    assert again.status_code == 409


async def test_initiator_is_notified_through_bot_api(
    client: httpx.AsyncClient, anna: Account, boris: Account, house: House,
    bot_headers: dict[str, str],
):  # fmt: skip
    await report(client, anna, house)
    await join(client, boris, await report(client, boris, house))
    carol = await neighbour(client, 5)
    await join(client, carol, await report(client, carol, house))

    pending = (await client.get("/bot/notifications", headers=bot_headers)).json()
    assert [(n["telegram_id"], n["text"]) for n in pending] == [
        (anna.telegram_id, "К вашему обращению присоединился сосед. Теперь вас 2."),
        (anna.telegram_id, "К вашему обращению присоединился сосед. Теперь вас 3."),
    ]
    assert set(pending[0]) == {"id", "telegram_id", "issue_id", "text"}

    done = await client.post(f"/bot/notifications/{pending[0]['id']}/sent", headers=bot_headers)
    assert done.status_code == 204
    left = (await client.get("/bot/notifications", headers=bot_headers)).json()
    assert [n["id"] for n in left] == [pending[1]["id"]]
    missing = await client.post(f"/bot/notifications/{uuid.uuid4()}/sent", headers=bot_headers)
    assert missing.status_code == 404


async def test_notifications_need_bot_token_and_skip_synthetic_users(
    client: httpx.AsyncClient, session: AsyncSession, boris: Account, house: House,
    resident: User, bot_headers: dict[str, str],
):  # fmt: skip
    assert (await client.get("/bot/notifications", headers=boris.headers)).status_code == 401
    session.add(Issue(user_id=resident.id, category="elevator", house_id=house.id,
                      addressee_key="managing_company", route={}))  # fmt: skip
    await session.flush()
    await join(client, boris, await report(client, boris, house))
    assert (await client.get("/bot/notifications", headers=bot_headers)).json() == []
