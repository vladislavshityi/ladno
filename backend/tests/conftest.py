import asyncio
import io
import os
import tempfile
from collections.abc import AsyncIterator
from dataclasses import dataclass
from pathlib import Path

# Настройки задаются до импорта приложения: тесты не зависят от локального .env.
os.environ.update(
    {
        "APP_ENV": "dev",
        "JWT_SECRET": "test-secret-for-tests-only-0123456789abcdef",
        "PII_ENCRYPTION_KEY": "dGVzdC1vbmx5LWtleS1mb3ItcGVyc29uYWwtZGF0YSE=",
        "LLM_PROVIDER": "none",
        "LLM_BASE_URL": "",
        "LLM_API_KEY": "",
        "LLM_MODEL": "",
        "LLM_VISION_MODEL": "",
        "DEMO_DATA": "false",
        "TELEGRAM_BOT_TOKEN": "123456:TEST-TOKEN",
        "TELEGRAM_BOT_USERNAME": "",
        "BOT_API_TOKEN": "test-bot-token",
        "UPLOAD_DIR": tempfile.mkdtemp(prefix="ladno-test-uploads-"),
    }
)

import httpx
import pytest
import pytest_asyncio
from alembic import command
from alembic.config import Config
from fastapi import FastAPI
from PIL import Image
from sqlalchemy import select, text
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    create_async_engine,
)

from app.core.config import get_settings
from app.core.db import get_session
from app.core.rate_limit import reset_rate_limits
from app.llm.client import get_llm
from app.main import create_app
from app.modules.houses.models import House
from app.modules.houses.service import seed_houses
from app.modules.ratings import service as ratings
from app.modules.users.models import User

BACKEND_DIR = Path(__file__).resolve().parents[1]


def _test_url() -> str:
    url = make_url(get_settings().database_url)
    return url.set(database=f"{url.database}_test").render_as_string(hide_password=False)


@pytest_asyncio.fixture(scope="session")
async def engine() -> AsyncIterator[AsyncEngine]:
    test_url = make_url(_test_url())
    admin = create_async_engine(test_url.set(database="postgres"), isolation_level="AUTOCOMMIT")
    async with admin.connect() as conn:
        await conn.execute(text(f'DROP DATABASE IF EXISTS "{test_url.database}" WITH (FORCE)'))
        await conn.execute(text(f'CREATE DATABASE "{test_url.database}"'))
    await admin.dispose()

    config = Config(str(BACKEND_DIR / "alembic.ini"))
    config.set_main_option("script_location", str(BACKEND_DIR / "alembic"))
    config.set_main_option("sqlalchemy.url", test_url.render_as_string(hide_password=False))
    await asyncio.to_thread(command.upgrade, config, "head")

    engine = create_async_engine(test_url)
    async with AsyncSession(engine) as seeding:
        await seed_houses(seeding)
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture
async def session(engine: AsyncEngine) -> AsyncIterator[AsyncSession]:
    async with engine.connect() as connection:
        transaction = await connection.begin()
        async with AsyncSession(
            bind=connection, join_transaction_mode="create_savepoint", expire_on_commit=False
        ) as db_session:
            yield db_session
        await transaction.rollback()


class FakeLLM:
    """Языковая модель без сети: отдаёт заготовленные ответы и запоминает запросы."""

    def __init__(self) -> None:
        self.replies: list[str] = []
        self.chunks: list[str] = []
        self.calls: list[list[dict]] = []
        self.models: list[str | None] = []
        self.error: Exception | None = None

    async def complete(
        self, messages: list[dict], *, json_mode: bool = False, model: str | None = None
    ) -> str:
        self.calls.append(messages)
        self.models.append(model)
        if self.error:
            raise self.error
        return self.replies.pop(0) if len(self.replies) > 1 else self.replies[0]

    async def stream(self, messages: list[dict]) -> AsyncIterator[str]:
        self.calls.append(messages)
        for chunk in self.chunks:
            yield chunk
        if self.error:
            raise self.error


@pytest.fixture(autouse=True)
def _fresh_rate_limits() -> None:
    reset_rate_limits()


@pytest.fixture(autouse=True)
def _fresh_ratings_cache() -> None:
    ratings.reset_cache()


@pytest.fixture
def app() -> FastAPI:
    return create_app()


@pytest.fixture
def llm(app: FastAPI) -> FakeLLM:
    """Подменяет модель приложения; без этой фикстуры модель не настроена (LLM_PROVIDER=none)."""
    fake = FakeLLM()
    app.dependency_overrides[get_llm] = lambda: fake
    return fake


@pytest_asyncio.fixture
async def client(app: FastAPI, session: AsyncSession) -> AsyncIterator[httpx.AsyncClient]:
    async def override_session() -> AsyncIterator[AsyncSession]:
        yield session

    app.dependency_overrides[get_session] = override_session
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test/api") as http:
        yield http


def make_png(exif: bytes | None = None) -> bytes:
    """Настоящая картинка 4×4: загрузка фото пересохраняет её через Pillow."""
    out = io.BytesIO()
    Image.new("RGB", (4, 4), "white").save(out, format="PNG", exif=exif or b"")
    return out.getvalue()


PNG = make_png()


@dataclass
class Account:
    id: str
    telegram_id: int
    headers: dict[str, str]


async def dev_login(client: httpx.AsyncClient, telegram_id: int, consent: bool = True) -> Account:
    response = await client.post("/auth/dev", json={"telegram_id": telegram_id})
    assert response.status_code == 200, response.text
    body = response.json()
    headers = {"Authorization": f"Bearer {body['access_token']}"}
    if consent:
        version = get_settings().consent_version
        await client.post("/users/me/consent", json={"version": version}, headers=headers)
    return Account(body["user"]["id"], telegram_id, headers)


@pytest_asyncio.fixture
async def anna(client: httpx.AsyncClient) -> Account:
    return await dev_login(client, 1001)


@pytest_asyncio.fixture
async def boris(client: httpx.AsyncClient) -> Account:
    return await dev_login(client, 1002)


@pytest_asyncio.fixture
async def newcomer(client: httpx.AsyncClient) -> Account:
    """Вошёл, но согласия на обработку данных ещё не дал."""
    return await dev_login(client, 1003, consent=False)


@pytest.fixture
def bot_headers() -> dict[str, str]:
    return {"Authorization": "Bearer test-bot-token"}


@pytest.fixture
def prod_mode(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("APP_ENV", "prod")
    get_settings.cache_clear()
    yield
    monkeypatch.undo()
    get_settings.cache_clear()


@pytest_asyncio.fixture
async def house(session: AsyncSession) -> House:
    """Дом из справочника с известными УК и координатами."""
    found = await session.scalars(
        select(House)
        .where(House.management_company_id.is_not(None), House.lat.is_not(None))
        .order_by(House.id)
        .limit(1)
    )
    return found.one()


@pytest_asyncio.fixture
async def resident(session: AsyncSession) -> User:
    user = User(telegram_id=-777)
    session.add(user)
    await session.flush()
    return user
