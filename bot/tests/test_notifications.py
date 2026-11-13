from unittest.mock import AsyncMock

from aiogram.exceptions import TelegramAPIError, TelegramForbiddenError
from aiogram.methods import SendMessage

from bot.notifications import send_notifications
from tests.conftest import make_notification


def forbidden() -> TelegramForbiddenError:
    return TelegramForbiddenError(SendMessage(chat_id=1, text="x"), "bot was blocked")


async def test_notification_is_sent_with_issue_button_and_marked(settings):
    item = make_notification()
    bot, api = AsyncMock(), AsyncMock()
    api.notifications.return_value = [item]

    await send_notifications(bot, api, settings)

    chat_id, text = bot.send_message.await_args.args
    assert chat_id == 42 and text == item.text
    keyboard = bot.send_message.await_args.kwargs["reply_markup"].inline_keyboard
    assert keyboard[0][0].web_app.url.endswith(f"/issues/{item.issue_id}")
    api.mark_notification_sent.assert_awaited_once_with(item.id)


async def test_blocked_user_is_marked_and_failure_is_retried(settings):
    blocked, failing, fine = (make_notification(telegram_id=n) for n in (1, 2, 3))
    bot, api = AsyncMock(), AsyncMock()
    bot.send_message.side_effect = [
        forbidden(),
        TelegramAPIError(SendMessage(chat_id=2, text="x"), "boom"),
        None,
    ]
    api.notifications.return_value = [blocked, failing, fine]

    await send_notifications(bot, api, settings)

    marked = [call.args[0] for call in api.mark_notification_sent.await_args_list]
    assert marked == [
        blocked.id,
        fine.id,
    ]  # сбой Telegram не отмечается: придёт при следующем проходе
