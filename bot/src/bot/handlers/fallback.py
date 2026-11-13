from aiogram import Router
from aiogram.types import Message

from bot import texts
from bot.config import Settings
from bot.keyboards import ISSUE_NEW, app_keyboard

router = Router()


@router.message()
async def open_app(message: Message, settings: Settings) -> None:
    """Любой текст или фото: бот не дублирует логику, а ведёт в приложение."""
    keyboard = app_keyboard(settings, ("Описать проблему", ISSUE_NEW))
    await message.answer(texts.FALLBACK, reply_markup=keyboard)
