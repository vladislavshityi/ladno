from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from bot import texts
from bot.api import BackendClient
from bot.config import Settings
from bot.keyboards import ISSUE_NEW, ISSUES, app_keyboard, issue_path

router = Router()


@router.message(Command("issues"))
async def my_issues(message: Message, settings: Settings, api: BackendClient) -> None:
    if message.from_user is None:
        return
    issues = await api.user_issues(message.from_user.id)
    if not issues:
        keyboard = app_keyboard(settings, ("Создать обращение", ISSUE_NEW))
        await message.answer(texts.NO_ISSUES, reply_markup=keyboard)
        return
    buttons = [(i.category_title, issue_path(i.id)) for i in issues]
    keyboard = app_keyboard(settings, *buttons, ("Все обращения", ISSUES))
    await message.answer(texts.issues_list(issues), reply_markup=keyboard)
