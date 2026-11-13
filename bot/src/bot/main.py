import asyncio
import logging

from aiogram import Bot, Dispatcher, F
from aiogram.types import MenuButtonWebApp, WebAppInfo

from bot.api import BackendClient
from bot.config import Settings, get_settings
from bot.handlers import routers
from bot.notifications import run_notifications
from bot.reminders import run_reminders

log = logging.getLogger(__name__)


async def set_menu_button(bot: Bot, settings: Settings) -> None:
    if settings.app_is_https:
        button = MenuButtonWebApp(text="Ладно", web_app=WebAppInfo(url=settings.app_url("/")))
        await bot.set_chat_menu_button(menu_button=button)


async def main() -> None:
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s"
    )
    # Адреса запросов содержат telegram_id пользователей.
    logging.getLogger("httpx").setLevel(logging.WARNING)

    settings = get_settings()
    bot = Bot(settings.telegram_bot_token)
    api = BackendClient(settings.backend_url, settings.bot_api_token)
    dp = Dispatcher(settings=settings, api=api)
    dp.message.filter(F.chat.type == "private")
    dp.include_routers(*routers)

    await set_menu_button(bot, settings)
    background = [
        asyncio.create_task(run_reminders(bot, api, settings)),
        asyncio.create_task(run_notifications(bot, api, settings)),
    ]
    try:
        log.info("polling started")
        await dp.start_polling(bot)
    finally:
        for task in background:
            task.cancel()
        await api.close()
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
