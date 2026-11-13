from bot import texts
from bot.keyboards import app_button, issue_path, main_menu
from tests.conftest import make_issue, make_reminder, make_settings


def test_https_uses_web_app():
    button = app_button(make_settings(), "Открыть", "/issues/new")
    assert button.web_app.url == "https://ladno.example/issues/new" and button.url is None


def test_plain_http_uses_url_button():
    button = app_button(make_settings("http://192.168.1.5:8080/"), "Открыть", "/receipts")
    assert button.url == "http://192.168.1.5:8080/receipts" and button.web_app is None


def test_main_menu_links_to_app_routes():
    rows = main_menu(make_settings()).inline_keyboard
    assert [r[0].web_app.url.removeprefix("https://ladno.example") for r in rows] == [
        "/issues/new",
        "/receipts",
        "/issues",
    ]


def test_issue_line_shows_deadline_and_overdue():
    line = texts.issue_line(make_issue(is_overdue=True))
    assert "подано" in line and "УК «Центр»" in line
    assert "01.12.2026 (просрочено)" in line
    assert "Ответ до" not in texts.issue_line(make_issue(deadline_at=None, status="draft"))


def test_reminder_text_for_overdue_and_upcoming():
    assert "истёк 01.11.2026" in texts.reminder_text(make_reminder())
    assert "истекает" in texts.reminder_text(make_reminder(is_overdue=False))


def test_issue_path():
    assert issue_path("abc") == "/issues/abc"
