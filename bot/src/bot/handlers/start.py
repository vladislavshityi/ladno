from aiogram import Router
from aiogram.filters import Command, CommandStart
from aiogram.types import Message

from bot import texts
from bot.config import Settings
from bot.keyboards import ISSUE_NEW, RECEIPTS, app_keyboard, main_menu

router = Router()


@router.message(CommandStart())
@router.message(Command("help"))
async def welcome(message: Message, settings: Settings) -> None:
    text = texts.WELCOME if settings.app_is_https else texts.WELCOME + texts.NOT_HTTPS
    await message.answer(text, reply_markup=main_menu(settings))


@router.message(Command("issue"))
async def new_issue(message: Message, settings: Settings) -> None:
    keyboard = app_keyboard(settings, ("Кому пожаловаться?", ISSUE_NEW))
    await message.answer(texts.OPEN_ISSUE, reply_markup=keyboard)


@router.message(Command("receipt"))
async def receipt(message: Message, settings: Settings) -> None:
    keyboard = app_keyboard(settings, ("Объясни мою квитанцию", RECEIPTS))
    await message.answer(texts.OPEN_RECEIPT, reply_markup=keyboard)
