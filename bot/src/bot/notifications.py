import asyncio
import logging

import httpx
from aiogram import Bot
from aiogram.exceptions import TelegramAPIError, TelegramForbiddenError

from bot.api import BackendClient
from bot.config import Settings
from bot.keyboards import app_keyboard, issue_path

log = logging.getLogger(__name__)

# Сообщения вроде «присоединился сосед» ждут не часами: очередь проверяется чаще напоминаний.
POLL_SECONDS = 60


async def send_notifications(bot: Bot, api: BackendClient, settings: Settings) -> None:
    """Один проход: отправить сообщения из очереди backend и отметить их отправленными."""
    for item in await api.notifications():
        keyboard = app_keyboard(settings, ("Открыть обращение", issue_path(item.issue_id)))
        try:
            await bot.send_message(item.telegram_id, item.text, reply_markup=keyboard)
        except TelegramForbiddenError:
            # Бот заблокирован: отмечаем отправленным, иначе сообщение будет повторяться.
            log.warning("Пользователь закрыл чат с ботом, сообщение %s", item.id)
        except TelegramAPIError:
            log.exception("Не удалось отправить сообщение %s", item.id)
            continue
        await api.mark_notification_sent(item.id)


async def run_notifications(bot: Bot, api: BackendClient, settings: Settings) -> None:
    while True:
        try:
            await send_notifications(bot, api, settings)
        except httpx.HTTPError:
            log.exception("Backend недоступен, сообщения отложены")
        await asyncio.sleep(POLL_SECONDS)
