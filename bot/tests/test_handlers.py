from unittest.mock import AsyncMock

from bot import texts
from bot.handlers.fallback import open_app
from bot.handlers.issues import my_issues
from bot.handlers.start import welcome
from tests.conftest import make_issue, make_settings


def sent_keyboard(message):
    return message.answer.await_args.kwargs["reply_markup"].inline_keyboard


async def test_start_greets_with_three_buttons(message, settings):
    await welcome(message, settings)
    assert message.answer.await_args.args[0] == texts.WELCOME
    assert len(sent_keyboard(message)) == 3


async def test_start_explains_non_https(message):
    await welcome(message, make_settings("http://localhost:8080"))
    assert texts.NOT_HTTPS in message.answer.await_args.args[0]


async def test_issues_lists_with_links_to_cards(message, settings):
    issue = make_issue()
    api = AsyncMock()
    api.user_issues.return_value = [issue]
    await my_issues(message, settings, api)
    api.user_issues.assert_awaited_once_with(42)
    urls = [row[0].web_app.url for row in sent_keyboard(message)]
    assert urls[0] == f"https://ladno.example/issues/{issue.id}"
    assert issue.category_title in message.answer.await_args.args[0]


async def test_issues_empty_offers_to_create(message, settings):
    api = AsyncMock()
    api.user_issues.return_value = []
    await my_issues(message, settings, api)
    assert message.answer.await_args.args[0] == texts.NO_ISSUES
    assert sent_keyboard(message)[0][0].web_app.url.endswith("/issues/new")


async def test_any_message_points_to_app(message, settings):
    await open_app(message, settings)
    assert message.answer.await_args.args[0] == texts.FALLBACK
