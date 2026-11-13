"""Строка «От:» для писем: данные жителя подставляет код, пустые поля остаются метками."""

from app.modules.users.models import User

PLACEHOLDERS = {
    "full_name": "[укажите ФИО]",
    "apartment": "[укажите номер]",
    "phone": "[укажите телефон]",
}


def applicant_line(user: User) -> str:
    """«Иванов И. И., кв. 12, тел. +7...»; чего нет в профиле, то пометка «[укажите …]»."""
    parts = [
        user.full_name or PLACEHOLDERS["full_name"],
        f"кв. {user.apartment or PLACEHOLDERS['apartment']}",
        f"тел. {user.phone or PLACEHOLDERS['phone']}",
    ]
    if user.email:
        parts.append(f"e-mail {user.email}")
    return ", ".join(parts)


def missing_fields(text: str) -> list[str]:
    """Какие данные жителя в тексте письма остались пометками."""
    return [field for field, mark in PLACEHOLDERS.items() if mark in text]
