from unittest.mock import AsyncMock

from aiogram.exceptions import TelegramForbiddenError
from aiogram.methods import SendMessage

from bot.reminders import send_reminders
from tests.conftest import make_reminder


def forbidden() -> TelegramForbiddenError:
    return TelegramForbiddenError(SendMessage(chat_id=1, text="x"), "bot was blocked")


async def test_reminder_is_sent_with_buttons_and_marked(settings):
    reminder = make_reminder()
    bot, api = AsyncMock(), AsyncMock()
    api.reminders.return_value = [reminder]

    await send_reminders(bot, api, settings)

    chat_id, text = bot.send_message.await_args.args
    assert chat_id == 42 and "истёк" in text
    keyboard = bot.send_message.await_args.kwargs["reply_markup"].inline_keyboard
    assert [row[0].text for row in keyboard] == ["Открыть обращение", "Эскалировать"]
    assert keyboard[0][0].web_app.url.endswith(f"/issues/{reminder.issue_id}")
    api.mark_reminder_sent.assert_awaited_once_with(reminder.issue_id)


async def test_blocked_user_does_not_stop_the_rest(settings):
    blocked, fine = make_reminder(telegram_id=1), make_reminder(telegram_id=2)
    bot, api = AsyncMock(), AsyncMock()
    bot.send_message.side_effect = [forbidden(), None]
    api.reminders.return_value = [blocked, fine]

    await send_reminders(bot, api, settings)

    assert bot.send_message.await_count == 2
    marked = [call.args[0] for call in api.mark_reminder_sent.await_args_list]
    assert marked == [blocked.issue_id, fine.issue_id]
