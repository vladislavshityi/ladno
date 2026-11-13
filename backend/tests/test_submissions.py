import smtplib
import uuid
from email.message import EmailMessage
from typing import ClassVar

import httpx
import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.modules.issues.models import Issue
from app.modules.submissions.models import AttemptStatus, SubmissionAttempt
from tests.conftest import PNG, Account, dev_login

GRAFFITI = {"category": "graffiti", "answers": {"place": "entrance"}}
UK_EMAIL = "uk@example.org"


class FakeSMTP:
    """Почтовый сервер без сети: запоминает письма и при необходимости падает."""

    sent: ClassVar[list[EmailMessage]] = []
    fail: ClassVar[bool] = False

    def __init__(self, host: str, port: int, **kwargs: object) -> None:
        pass

    def __enter__(self) -> "FakeSMTP":
        return self

    def __exit__(self, *args: object) -> None:
        pass

    def starttls(self, **kwargs: object) -> None:
        pass

    def login(self, user: str, password: str) -> None:
        pass

    def send_message(self, message: EmailMessage) -> None:
        if FakeSMTP.fail:
            raise smtplib.SMTPServerDisconnected("secret@example.org")
        FakeSMTP.sent.append(message)


@pytest.fixture
def smtp(monkeypatch: pytest.MonkeyPatch) -> type[FakeSMTP]:
    monkeypatch.setenv("SMTP_HOST", "smtp.test")
    monkeypatch.setenv("SMTP_FROM", "ladno@example.org")
    get_settings.cache_clear()
    monkeypatch.setattr(smtplib, "SMTP", FakeSMTP)
    FakeSMTP.sent, FakeSMTP.fail = [], False
    yield FakeSMTP
    monkeypatch.undo()
    get_settings.cache_clear()


async def create_issue(
    client: httpx.AsyncClient, session: AsyncSession, who: Account, email: str | None = UK_EMAIL
) -> str:
    photo = await client.post("/photos", files={"file": ("a.png", PNG)}, headers=who.headers)
    payload = {**GRAFFITI, "photo_ids": [photo.json()["id"]], "description": "Надпись на стене"}
    created = await client.post("/issues", json=payload, headers=who.headers)
    assert created.status_code == 201, created.text
    issue_id = created.json()["id"]
    if email:  # у УК из справочника почты может не быть: добавляем адресату канал вручную
        issue = await session.get(Issue, uuid.UUID(issue_id))
        route = dict(issue.route)
        route["addressee"] = {
            **route["addressee"],
            "channels": [{"type": "email", "value": email, "label": "Почта УК"}],
        }
        issue.route = route
        await session.commit()
    return issue_id


async def channel_names(client: httpx.AsyncClient, who: Account, issue_id: str) -> list[str]:
    response = await client.get(f"/issues/{issue_id}/channels", headers=who.headers)
    assert response.status_code == 200, response.text
    return [c["name"] for c in response.json()]


async def test_letter_pdf_contains_text_and_photo(
    client: httpx.AsyncClient, session: AsyncSession, anna: Account, boris: Account
):
    issue_id = await create_issue(client, session, anna, email=None)
    response = await client.get(f"/issues/{issue_id}/letter.pdf", headers=anna.headers)
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert response.content.startswith(b"%PDF")
    assert b"/Subtype /Image" in response.content or b"/Image" in response.content
    other = await client.get(f"/issues/{issue_id}/letter.pdf", headers=boris.headers)
    assert other.status_code == 404


async def test_letter_mentions_photos_count(
    client: httpx.AsyncClient, session: AsyncSession, anna: Account
):
    issue_id = await create_issue(client, session, anna, email=None)
    issue = (await client.get(f"/issues/{issue_id}", headers=anna.headers)).json()
    assert "Приложения: фотографии, 1 шт." in issue["draft"]["full"]


async def test_channels_manual_only_without_smtp(
    client: httpx.AsyncClient, session: AsyncSession, anna: Account
):
    issue_id = await create_issue(client, session, anna)
    assert await channel_names(client, anna, issue_id) == ["manual"]
    response = await client.post(
        f"/issues/{issue_id}/send", json={"channel": "email"}, headers=anna.headers
    )
    assert (response.status_code, response.json()["code"]) == (404, "channel_unavailable")


async def test_channels_need_recipient_email(
    client: httpx.AsyncClient, session: AsyncSession, anna: Account, smtp: type[FakeSMTP]
):
    without = await create_issue(client, session, anna, email=None)
    with_email = await create_issue(client, session, anna)
    assert await channel_names(client, anna, without) == ["manual"]
    assert await channel_names(client, anna, with_email) == ["manual", "email"]


async def test_email_send_marks_submitted(
    client: httpx.AsyncClient, session: AsyncSession, anna: Account, smtp: type[FakeSMTP]
):
    await client.put("/users/me/profile", json={"email": "anna@example.org"}, headers=anna.headers)
    issue_id = await create_issue(client, session, anna)
    response = await client.post(
        f"/issues/{issue_id}/send", json={"channel": "email"}, headers=anna.headers
    )
    assert response.status_code == 200, response.text
    (message,) = smtp.sent
    assert message["To"] == UK_EMAIL
    assert message["Reply-To"] == message["Cc"] == "anna@example.org"
    attachments = [p.get_filename() for p in message.iter_attachments()]
    assert attachments == ["letter.pdf", "photo-1.png"]
    issue = (await client.get(f"/issues/{issue_id}", headers=anna.headers)).json()
    assert issue["status"] == "submitted" and issue["submitted_at"]
    assert issue["external_ref"] == response.json()["external_ref"]
    attempts = (await session.scalars(select(SubmissionAttempt))).all()
    assert [(a.channel, a.status) for a in attempts] == [("email", AttemptStatus.SENT)]


async def test_email_without_profile_email_has_no_copy(
    client: httpx.AsyncClient, session: AsyncSession, anna: Account, smtp: type[FakeSMTP]
):
    issue_id = await create_issue(client, session, anna)
    await client.post(f"/issues/{issue_id}/send", json={"channel": "email"}, headers=anna.headers)
    assert smtp.sent[0]["Cc"] is None and smtp.sent[0]["Reply-To"] is None


async def test_failed_send_is_recorded_without_leaking_details(
    client: httpx.AsyncClient, session: AsyncSession, anna: Account, smtp: type[FakeSMTP]
):
    smtp.fail = True
    issue_id = await create_issue(client, session, anna)
    response = await client.post(
        f"/issues/{issue_id}/send", json={"channel": "email"}, headers=anna.headers
    )
    assert (response.status_code, response.json()["code"]) == (502, "send_failed")
    assert "secret@example.org" not in response.text
    (attempt,) = (await session.scalars(select(SubmissionAttempt))).all()
    assert attempt.status == AttemptStatus.FAILED and attempt.error == "SMTPServerDisconnected"
    issue = (await client.get(f"/issues/{issue_id}", headers=anna.headers)).json()
    assert issue["status"] == "draft"


async def test_send_limit_per_issue(
    client: httpx.AsyncClient, session: AsyncSession, anna: Account, smtp: type[FakeSMTP]
):
    issue_id = await create_issue(client, session, anna)
    for _ in range(3):
        ok = await client.post(
            f"/issues/{issue_id}/send", json={"channel": "email"}, headers=anna.headers
        )
        assert ok.status_code == 200
    extra = await client.post(
        f"/issues/{issue_id}/send", json={"channel": "email"}, headers=anna.headers
    )
    assert (extra.status_code, extra.json()["code"]) == (429, "send_limit_reached")
    assert len(smtp.sent) == 3


async def test_send_rules(
    client: httpx.AsyncClient,
    session: AsyncSession,
    anna: Account,
    boris: Account,
    smtp: type[FakeSMTP],
):
    issue_id = await create_issue(client, session, anna)
    body = {"channel": "email"}
    assert (
        await client.post(f"/issues/{issue_id}/send", json=body, headers=boris.headers)
    ).status_code == 404
    assert (
        await client.get(f"/issues/{issue_id}/channels", headers=boris.headers)
    ).status_code == 404
    manual = await client.post(
        f"/issues/{issue_id}/send", json={"channel": "manual"}, headers=anna.headers
    )
    assert (manual.status_code, manual.json()["code"]) == (409, "manual_channel")
    newcomer = await dev_login(client, 1003, consent=False)
    denied = await client.post(f"/issues/{issue_id}/send", json=body, headers=newcomer.headers)
    assert denied.status_code == 403
    assert smtp.sent == []
