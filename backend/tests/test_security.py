"""Безопасность: токены, закрытые в проде страницы, файлы, публичные данные, почтовые адреса."""

import asyncio
import io
from datetime import timedelta
from pathlib import Path

import httpx
import jwt
import pytest
from PIL import Image
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import DEV_JWT_SECRET, DEV_PII_KEY, Settings, get_settings
from app.core.db import utcnow
from app.core.fields import normalize_email
from app.main import create_app
from app.modules.houses.models import House
from app.modules.houses.service import _web_address
from app.modules.issues.models import IssueStatus
from app.modules.users.models import User
from tests.conftest import PNG, Account
from tests.issue_factory import add, make_issue


def token(claims: dict, secret: str | None = None, algorithm: str = "HS256") -> str:
    return jwt.encode(claims, secret or get_settings().jwt_secret, algorithm=algorithm)


# --- токены ---


async def test_token_without_expiry_is_rejected(client: httpx.AsyncClient, anna: Account):
    forever = token({"sub": anna.id})
    response = await client.get("/users/me", headers={"Authorization": f"Bearer {forever}"})
    assert response.status_code == 401


async def test_expired_alien_and_unsigned_tokens_are_rejected(
    client: httpx.AsyncClient, anna: Account
):
    soon = utcnow() + timedelta(hours=1)
    tokens = [
        token({"sub": anna.id, "exp": utcnow() - timedelta(seconds=5)}),
        token({"sub": anna.id, "exp": soon}, secret="another-secret-0123456789abcdef-xyz"),
        jwt.encode({"sub": anna.id, "exp": soon}, None, algorithm="none"),
        token({"sub": anna.id, "exp": soon}, algorithm="HS512"),
        token({"exp": soon}),
        token({"sub": "not-a-uuid", "exp": soon}),
        "garbage",
    ]
    for value in tokens:
        response = await client.get("/users/me", headers={"Authorization": f"Bearer {value}"})
        assert response.status_code == 401, value


async def test_token_of_deleted_user_stops_working(client: httpx.AsyncClient, anna: Account):
    assert (await client.delete("/users/me", headers=anna.headers)).status_code == 204
    for url in ("/users/me", "/issues"):
        response = await client.get(url, headers=anna.headers)
        assert response.status_code == 401 and response.json()["code"] == "invalid_token"


def test_prod_refuses_default_secrets():
    with pytest.raises(ValidationError):
        Settings(app_env="prod", jwt_secret=DEV_JWT_SECRET, pii_encryption_key="x" * 44)
    with pytest.raises(ValidationError):
        Settings(app_env="prod", jwt_secret="s" * 40, pii_encryption_key=DEV_PII_KEY)
    assert Settings(app_env="prod", jwt_secret="s" * 40, pii_encryption_key="k" * 44)


# --- закрытое в проде и заголовки ---


async def test_docs_are_open_in_dev_and_closed_in_prod(prod_mode: None):
    prod = create_app()
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=prod), base_url="http://t") as c:
        for url in ("/docs", "/redoc", "/openapi.json"):
            assert (await c.get(url)).status_code == 404, url
    get_settings.cache_clear()


async def test_docs_are_open_in_dev(client: httpx.AsyncClient, app):
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://t") as plain:
        assert (await plain.get("/openapi.json")).status_code == 200


async def test_api_responses_forbid_content_sniffing(client: httpx.AsyncClient):
    response = await client.get("/faq")
    assert response.headers["X-Content-Type-Options"] == "nosniff"


# --- файлы ---


async def upload(client: httpx.AsyncClient, who: Account, data: bytes, name: str, kind: str):
    return await client.post("/photos", files={"file": (name, data, kind)}, headers=who.headers)


async def test_only_real_raster_images_are_accepted(client: httpx.AsyncClient, anna: Account):
    svg = b'<svg xmlns="http://www.w3.org/2000/svg"><script>alert(1)</script></svg>'
    for data, name, kind in [
        (svg, "a.png", "image/png"),
        (b"<html><script>alert(1)</script></html>", "a.jpg", "image/jpeg"),
        (b"GIF89a" + b"\x00" * 40, "a.png", "image/png"),
        (PNG[:20], "broken.png", "image/png"),  # сигнатура верна, картинка битая
        (b"%PDF-1.7\n" + b"0" * 32, "a.png", "image/png"),  # PDF как фото обращения
    ]:
        response = await upload(client, anna, data, name, kind)
        assert response.status_code in (415, 422), (name, response.text)


async def test_huge_pixel_count_image_is_rejected(client: httpx.AsyncClient, anna: Account):
    out = io.BytesIO()
    Image.new("1", (9000, 9000)).save(out, format="PNG")  # 81 млн пикселей в нескольких КБ
    assert out.tell() < 5 * 1024 * 1024
    response = await upload(client, anna, out.getvalue(), "bomb.png", "image/png")
    assert response.status_code == 415


async def test_file_name_never_reaches_disk_and_download_is_hardened(
    client: httpx.AsyncClient, anna: Account
):
    evil = "../../../etc/passwd.png"
    photo = (await upload(client, anna, PNG, evil, "image/png")).json()
    downloaded = await client.get(photo["url"].removeprefix("/api"), headers=anna.headers)
    assert downloaded.headers["content-type"] == "image/png"
    assert downloaded.headers["x-content-type-options"] == "nosniff"
    assert "sandbox" in downloaded.headers["content-security-policy"]
    photos_dir = Path(get_settings().upload_dir, "photos")
    stored = await asyncio.to_thread(lambda: list(photos_dir.glob("*")))
    assert stored and all(p.parent == photos_dir for p in stored)
    assert all(p.suffix in (".png", ".jpg", ".webp") and "passwd" not in p.name for p in stored)


async def test_exif_location_is_stripped_from_stored_photos(
    client: httpx.AsyncClient, anna: Account
):
    from tests.conftest import make_png

    exif = Image.Exif()
    exif[0x010F] = "SecretPhoneMaker"
    photo = (await upload(client, anna, make_png(exif.tobytes()), "a.png", "image/png")).json()
    data = (await client.get(photo["url"].removeprefix("/api"), headers=anna.headers)).content
    assert b"SecretPhoneMaker" not in data


# --- публичные данные ---


async def test_map_hides_houses_with_few_issues(
    client: httpx.AsyncClient, session: AsyncSession, resident: User, house: House, monkeypatch
):
    monkeypatch.setenv("MAP_MIN_ISSUES", "3")
    get_settings.cache_clear()
    try:
        await add(
            session,
            make_issue(resident, house, IssueStatus.SUBMITTED),
            make_issue(resident, house, IssueStatus.SUBMITTED),
        )
        assert (await client.get("/map/points")).json() == []
        await add(session, make_issue(resident, house, IssueStatus.SUBMITTED))
        (point,) = (await client.get("/map/points")).json()
        assert point["total"] == 3
        # с фильтром по категории порог тоже применяется к тому, что осталось
        assert (await client.get("/map/points", params={"category": "garbage"})).json() == []
    finally:
        monkeypatch.undo()
        get_settings.cache_clear()


# --- адреса ---


@pytest.mark.parametrize(
    "bad",
    [
        "a,evil@example.org",
        "a@example.org,evil@example.org",
        "a;b@example.org",
        'a"b@example.org',
        "<a@example.org>",
        "a b@example.org",
        "a@example.org\r\nBcc: evil@example.org",
        "a@@example.org",
    ],
)
def test_email_cannot_carry_extra_recipients_or_headers(bad: str):
    with pytest.raises(ValueError):
        normalize_email(bad)


@pytest.mark.parametrize(
    "good", ["ivan.petrov+uk@mail.ru", "Анна@почта.рф", "a_b-c@sub.example.org"]
)
def test_normal_emails_pass(good: str):
    assert normalize_email(good) == good.lower()


def test_company_site_must_be_web_address():
    assert _web_address("javascript:alert(1)") is None
    assert _web_address("data:text/html,<script>") is None
    assert _web_address("//evil.example") is None
    assert _web_address(" https://uk.example/ ") == "https://uk.example/"
    assert _web_address("HTTP://uk.example") == "HTTP://uk.example"
    assert _web_address("") is None


async def test_non_ascii_secrets_are_rejected_not_crashing(client: httpx.AsyncClient):
    bot = await client.get("/bot/reminders", headers={"Authorization": "Bearer секрет".encode()})
    assert bot.status_code == 401
    fields = {"id": "1", "auth_date": str(int(utcnow().timestamp())), "hash": "хэш"}
    assert (await client.post("/auth/telegram/widget", json=fields)).status_code == 401
    no_hash = {"id": 1, "auth_date": int(utcnow().timestamp())}
    assert (await client.post("/auth/telegram/widget", json=no_hash)).status_code == 422
