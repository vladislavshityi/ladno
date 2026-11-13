import asyncio
import logging

import httpx
from aiogram import Bot
from aiogram.exceptions import TelegramAPIError, TelegramForbiddenError

from bot import texts
from bot.api import BackendClient, Reminder
from bot.config import Settings
from bot.keyboards import app_keyboard, issue_path

log = logging.getLogger(__name__)


async def _send(bot: Bot, settings: Settings, reminder: Reminder) -> None:
    path = issue_path(reminder.issue_id)
    keyboard = app_keyboard(settings, ("Открыть обращение", path), ("Эскалировать", path))
    await bot.send_message(
        reminder.telegram_id, texts.reminder_text(reminder), reply_markup=keyboard
    )


async def send_reminders(bot: Bot, api: BackendClient, settings: Settings) -> None:
    """Один проход: отправить напоминания и отметить их в backend."""
    for reminder in await api.reminders():
        try:
            await _send(bot, settings, reminder)
        except TelegramForbiddenError:
            # Бот заблокирован: отмечаем отправленным, иначе напоминание будет повторяться.
            log.warning("Пользователь закрыл чат с ботом, обращение %s", reminder.issue_id)
        except TelegramAPIError:
            log.exception("Не удалось отправить напоминание по обращению %s", reminder.issue_id)
            continue
        await api.mark_reminder_sent(reminder.issue_id)


async def run_reminders(bot: Bot, api: BackendClient, settings: Settings) -> None:
    while True:
        try:
            await send_reminders(bot, api, settings)
        except httpx.HTTPError:
            log.exception("Backend недоступен, напоминания отложены")
        await asyncio.sleep(settings.reminder_interval_minutes * 60)
