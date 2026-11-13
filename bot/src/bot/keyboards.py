from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo

from bot.config import Settings

ISSUE_NEW = "/issues/new"
ISSUES = "/issues"
RECEIPTS = "/receipts"


def issue_path(issue_id: object) -> str:
    return f"/issues/{issue_id}"


def app_button(settings: Settings, text: str, path: str) -> InlineKeyboardButton:
    """Mini App по https, иначе обычная ссылка (локальная разработка)."""
    url = settings.app_url(path)
    if settings.app_is_https:
        return InlineKeyboardButton(text=text, web_app=WebAppInfo(url=url))
    return InlineKeyboardButton(text=text, url=url)


def app_keyboard(settings: Settings, *buttons: tuple[str, str]) -> InlineKeyboardMarkup:
    """Одна кнопка на строку: (подпись, путь в приложении)."""
    return InlineKeyboardMarkup(
        inline_keyboard=[[app_button(settings, text, path)] for text, path in buttons]
    )


def main_menu(settings: Settings) -> InlineKeyboardMarkup:
    return app_keyboard(
        settings,
        ("Кому пожаловаться?", ISSUE_NEW),
        ("Объясни мою квитанцию", RECEIPTS),
        ("Мои обращения", ISSUES),
    )
