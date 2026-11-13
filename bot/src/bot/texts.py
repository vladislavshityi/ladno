from datetime import datetime

from bot.api import BotIssue, Reminder

WELCOME = (
    "Я «Ладно» — помощник жителя Владивостока по ЖКХ.\n\n"
    "• Кому пожаловаться. Опишите проблему дома или двора, и я подскажу, кому писать, "
    "на какие нормы ссылаться и в какой срок ждать ответа. Если ответа нет, помогу "
    "эскалировать обращение.\n"
    "• Разбор квитанции. Начисления простым языком, сравнение двух месяцев и готовое "
    "заявление на перерасчёт.\n\n"
    "Всё это в приложении, откройте его кнопкой ниже."
)
NOT_HTTPS = (
    "\n\nMini App открывается только по https. Сейчас адрес приложения другой, "
    "поэтому кнопки ведут по обычным ссылкам."
)
OPEN_ISSUE = "Откройте приложение, чтобы описать проблему: оно подскажет, кому писать."
OPEN_RECEIPT = "Откройте приложение, чтобы разобрать квитанцию."
NO_ISSUES = "У вас пока нет обращений. Создайте первое в приложении."
FALLBACK = "Откройте приложение, чтобы описать проблему или разобрать квитанцию."

STATUS_TITLES = {
    "draft": "черновик",
    "submitted": "подано",
    "in_progress": "рассматривается",
    "resolved": "решено",
    "no_response": "нет ответа",
    "rejected": "отказ",
}


def _date(value: datetime) -> str:
    return value.strftime("%d.%m.%Y")


def issue_line(issue: BotIssue) -> str:
    line = f"{issue.category_title}\n{STATUS_TITLES.get(issue.status, issue.status)}"
    line += f", адресат: {issue.addressee_name}"
    if issue.deadline_at:
        line += f"\nОтвет до {_date(issue.deadline_at)}"
        if issue.is_overdue:
            line += " (просрочено)"
    return line


def issues_list(issues: list[BotIssue]) -> str:
    return "Ваши обращения:\n\n" + "\n\n".join(issue_line(i) for i in issues)


def reminder_text(reminder: Reminder) -> str:
    when = _date(reminder.deadline_at)
    if reminder.is_overdue:
        head = f"Срок ответа по обращению «{reminder.category_title}» истёк {when}."
        tail = "Можно эскалировать обращение на следующую ступень."
    else:
        head = f"Срок ответа по обращению «{reminder.category_title}» истекает {when}."
        tail = "Если ответа не будет, обращение можно эскалировать."
    return f"{head}\nАдресат: {reminder.addressee_name}.\n{tail}"
