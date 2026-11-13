import uuid

import httpx
import pytest

from bot.api import BackendClient

ISSUE_ID = str(uuid.uuid4())


def client_with(handler) -> BackendClient:
    return BackendClient("http://backend:8000", "secret", httpx.MockTransport(handler))


async def test_user_issues_sends_token_and_parses():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/api/bot/users/42/issues"
        assert request.headers["Authorization"] == "Bearer secret"
        body = {"id": ISSUE_ID, "category_title": "Свет", "status": "draft", "addressee_name": "УК"}
        return httpx.Response(200, json=[body])

    issues = await client_with(handler).user_issues(42)
    assert [str(i.id) for i in issues] == [ISSUE_ID]
    assert issues[0].deadline_at is None and issues[0].is_overdue is False


async def test_unknown_user_has_no_issues():
    client = client_with(lambda request: httpx.Response(404, json={"detail": "нет"}))
    assert await client.user_issues(42) == []


async def test_server_error_is_raised():
    client = client_with(lambda request: httpx.Response(401))
    with pytest.raises(httpx.HTTPStatusError):
        await client.reminders()


async def test_mark_reminder_sent_posts():
    seen = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append((request.method, request.url.path))
        return httpx.Response(204)

    await client_with(handler).mark_reminder_sent(uuid.UUID(ISSUE_ID))
    assert seen == [("POST", f"/api/bot/reminders/{ISSUE_ID}/sent")]
