import uuid
from datetime import datetime

import httpx
from pydantic import BaseModel


class BotIssue(BaseModel):
    id: uuid.UUID
    category_title: str
    status: str
    addressee_name: str
    deadline_at: datetime | None = None
    is_overdue: bool = False


class Reminder(BaseModel):
    issue_id: uuid.UUID
    telegram_id: int
    category_title: str
    addressee_name: str
    deadline_at: datetime
    is_overdue: bool


class Notification(BaseModel):
    id: uuid.UUID
    telegram_id: int
    issue_id: uuid.UUID
    text: str


class BackendClient:
    """Служебный API backend: общий секрет в заголовке, пользовательские токены не нужны."""

    def __init__(
        self, base_url: str, token: str, transport: httpx.AsyncBaseTransport | None = None
    ):
        self._http = httpx.AsyncClient(
            base_url=f"{base_url.rstrip('/')}/api/bot",
            headers={"Authorization": f"Bearer {token}"},
            timeout=10,
            transport=transport,
        )

    async def user_issues(self, telegram_id: int) -> list[BotIssue]:
        """Обращения пользователя; пользователь, не заходивший в приложение, — пустой список."""
        response = await self._http.get(f"/users/{telegram_id}/issues")
        if response.status_code == httpx.codes.NOT_FOUND:
            return []
        response.raise_for_status()
        return [BotIssue.model_validate(item) for item in response.json()]

    async def reminders(self) -> list[Reminder]:
        response = await self._http.get("/reminders")
        response.raise_for_status()
        return [Reminder.model_validate(item) for item in response.json()]

    async def mark_reminder_sent(self, issue_id: uuid.UUID) -> None:
        response = await self._http.post(f"/reminders/{issue_id}/sent")
        response.raise_for_status()

    async def notifications(self) -> list[Notification]:
        response = await self._http.get("/notifications")
        response.raise_for_status()
        return [Notification.model_validate(item) for item in response.json()]

    async def mark_notification_sent(self, notification_id: uuid.UUID) -> None:
        response = await self._http.post(f"/notifications/{notification_id}/sent")
        response.raise_for_status()

    async def close(self) -> None:
        await self._http.aclose()
