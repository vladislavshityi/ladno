"""Строка «От:» для писем: данные жителя подставляет код, пустые поля остаются метками."""

from app.modules.users.models import User

PLACEHOLDERS = {"full_name": "{{ФИО}}", "apartment": "{{КВАРТИРА}}", "phone": "{{ТЕЛЕФОН}}"}


def applicant_line(user: User) -> str:
    """«Иванов И. И., кв. 12, тел. +7...»; чего нет в профиле, то метка для ручной вставки."""
    parts = [
        user.full_name or PLACEHOLDERS["full_name"],
        f"кв. {user.apartment or PLACEHOLDERS['apartment']}",
        f"тел. {user.phone or PLACEHOLDERS['phone']}",
    ]
    if user.email:
        parts.append(f"e-mail {user.email}")
    return ", ".join(parts)
