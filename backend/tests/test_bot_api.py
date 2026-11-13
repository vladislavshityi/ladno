from datetime import UTC, datetime, timedelta

import httpx

from tests.conftest import Account

DARK = {"category": "stairwell_lighting", "answers": {"scope": "floor"}}


async def submitted(client: httpx.AsyncClient, who: Account, days_ago: int) -> str:
    issue = (await client.post("/issues", json=DARK, headers=who.headers)).json()
    sent = (datetime.now(UTC) - timedelta(days=days_ago)).isoformat()
    patch = {"status": "submitted", "submitted_at": sent}
    await client.patch(f"/issues/{issue['id']}", json=patch, headers=who.headers)
    return issue["id"]


async def test_bot_endpoints_need_bot_token(client: httpx.AsyncClient, anna: Account):
    for headers in ({}, {"Authorization": "Bearer wrong"}, anna.headers):
        for url in ("/bot/reminders", f"/bot/users/{anna.telegram_id}/issues"):
            response = await client.get(url, headers=headers)
            assert response.status_code == 401, (url, headers)
            assert response.json()["code"] == "invalid_bot_token"


async def test_bot_token_is_not_a_user_token(
    client: httpx.AsyncClient, bot_headers: dict[str, str]
):
    assert (await client.get("/users/me", headers=bot_headers)).status_code == 401


async def test_user_issues_brief(
    client: httpx.AsyncClient, anna: Account, bot_headers: dict[str, str]
):
    await submitted(client, anna, days_ago=40)
    await client.post("/issues", json=DARK, headers=anna.headers)
    url = f"/bot/users/{anna.telegram_id}/issues"
    items = (await client.get(url, headers=bot_headers)).json()
    assert [i["status"] for i in items] == ["draft", "submitted"]
    assert items[1]["is_overdue"] is True and items[0]["deadline_at"] is None
    assert set(items[0]) == {"id", "category_title", "status", "addressee_name", "deadline_at",
                             "is_overdue"}  # fmt: skip
    assert (await client.get("/bot/users/424242/issues", headers=bot_headers)).status_code == 404


async def test_reminders_for_due_and_overdue_then_marked_sent(
    client: httpx.AsyncClient, anna: Account, boris: Account, bot_headers: dict[str, str]
):
    overdue = await submitted(client, anna, days_ago=40)
    await submitted(client, boris, days_ago=0)  # срок через две недели: рано
    await client.post("/issues", json=DARK, headers=boris.headers)  # черновик без срока

    reminders = (await client.get("/bot/reminders", headers=bot_headers)).json()
    assert [r["issue_id"] for r in reminders] == [overdue]
    assert reminders[0]["telegram_id"] == anna.telegram_id and reminders[0]["is_overdue"] is True

    sent = await client.post(f"/bot/reminders/{overdue}/sent", headers=bot_headers)
    assert sent.status_code == 204
    assert (await client.get("/bot/reminders", headers=bot_headers)).json() == []
    missing = await client.post(
        "/bot/reminders/00000000-0000-0000-0000-000000000000/sent", headers=bot_headers
    )
    assert missing.status_code == 404


async def test_resolved_issue_gets_no_reminder(
    client: httpx.AsyncClient, anna: Account, bot_headers: dict[str, str]
):
    issue_id = await submitted(client, anna, days_ago=40)
    await client.patch(f"/issues/{issue_id}", json={"status": "resolved"}, headers=anna.headers)
    assert (await client.get("/bot/reminders", headers=bot_headers)).json() == []
