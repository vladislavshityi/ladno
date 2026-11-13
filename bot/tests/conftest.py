import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from bot.api import BotIssue, Notification, Reminder
from bot.config import Settings


def make_settings(public_url: str = "https://ladno.example") -> Settings:
    return Settings(
        telegram_bot_token="123:token",
        bot_api_token="secret",
        public_url=public_url,
        _env_file=None,
    )


@pytest.fixture
def settings() -> Settings:
    return make_settings()


@pytest.fixture
def message() -> MagicMock:
    msg = MagicMock()
    msg.answer = AsyncMock()
    msg.from_user.id = 42
    return msg


def make_issue(**fields) -> BotIssue:
    data = {
        "id": uuid.uuid4(),
        "category_title": "Не горит свет в подъезде",
        "status": "submitted",
        "addressee_name": "УК «Центр»",
        "deadline_at": datetime(2026, 12, 1, tzinfo=UTC),
        "is_overdue": False,
    }
    return BotIssue(**{**data, **fields})


def make_reminder(**fields) -> Reminder:
    data = {
        "issue_id": uuid.uuid4(),
        "telegram_id": 42,
        "category_title": "Не горит свет в подъезде",
        "addressee_name": "УК «Центр»",
        "deadline_at": datetime(2026, 11, 1, tzinfo=UTC),
        "is_overdue": True,
    }
    return Reminder(**{**data, **fields})


def make_notification(**fields) -> Notification:
    data = {
        "id": uuid.uuid4(),
        "telegram_id": 42,
        "issue_id": uuid.uuid4(),
        "text": "К вашему обращению присоединился сосед. Теперь вас 2.",
    }
    return Notification(**{**data, **fields})
