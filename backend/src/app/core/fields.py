"""Типы полей ввода: обрезка, нормализация и проверка. Чистые функции, без IO.

Каждое сообщение об ошибке написано по-русски и годится для показа жителю.
"""

import re
import unicodedata
from datetime import date
from decimal import Decimal
from typing import Annotated

from pydantic import AfterValidator

_WORD = re.compile(r"[A-Za-zА-Яа-яЁё]+(?:[-'’][A-Za-zА-Яа-яЁё]+)*\.?")
_APARTMENT = re.compile(r"\d{1,4}(?:[a-zа-яё]|/\d{1,3})?")
_EMAIL = re.compile(r"[^@\s]{1,64}@[^@\s.]+(?:\.[^@\s.]+)*\.[^@\s.]{2,}")
_PHONE_CHARS = re.compile(r"\+?[\d\s()\-]+")
_PERIOD = re.compile(r"(\d{4})-(0[1-9]|1[0-2])")

PHONE_ERROR = "Введите номер в формате +7 900 123-45-67"
FIRST_PERIOD = (2020, 1)


def _has_control(text: str, multiline: bool) -> bool:
    allowed = "\n\t" if multiline else ""
    return any(unicodedata.category(c) == "Cc" and c not in allowed for c in text)


def clean_text(value: str | None, max_len: int, multiline: bool = False) -> str | None:
    """Обрезает пробелы, пустую строку превращает в None, отвергает управляющие символы."""
    if value is None:
        return None
    text = value.replace("\r\n", "\n").replace("\r", "\n").strip()
    if _has_control(text, multiline):
        raise ValueError("Недопустимые символы")
    if len(text) > max_len:
        raise ValueError(f"Не длиннее {max_len} символов")
    return text or None


def _title_word(word: str) -> str:
    parts = re.split(r"([-'’])", word)
    return "".join(p[:1].upper() + p[1:].lower() if p not in "-'’" else p for p in parts)


def normalize_full_name(value: str | None) -> str | None:
    """«иванов  иван» -> «Иванов Иван»: 2-3 слова из букв, дефиса и апострофа."""
    text = clean_text(value, 100)
    if text is None:
        return None
    words = text.split()
    if not 2 <= len(words) <= 3:
        raise ValueError("Укажите фамилию и имя, отчество по желанию")
    if not all(_WORD.fullmatch(w) for w in words):
        raise ValueError("ФИО: только буквы, дефис и апостроф")
    return " ".join(_title_word(w) for w in words)


def normalize_phone(value: str | None) -> str | None:
    """«8 (900) 123-45-67» -> «+7 900 123-45-67»."""
    text = clean_text(value, 32)
    if text is None:
        return None
    digits = re.sub(r"\D", "", text)
    if not _PHONE_CHARS.fullmatch(text) or "+" in text[1:]:
        raise ValueError(PHONE_ERROR)
    if text.startswith("+"):
        national = digits[1:] if digits.startswith("7") else ""
    elif len(digits) == 11 and digits[0] in "78":
        national = digits[1:]
    else:
        national = digits if len(digits) == 10 else ""
    if len(national) != 10 or national[0] in "01":
        raise ValueError(PHONE_ERROR)
    return f"+7 {national[:3]} {national[3:6]}-{national[6:8]}-{national[8:]}"


def normalize_email(value: str | None) -> str | None:
    text = clean_text(value, 200)
    if text is None:
        return None
    if not _EMAIL.fullmatch(text):
        raise ValueError("Введите e-mail в формате name@example.ru")
    return text.lower()


def normalize_apartment(value: str | None) -> str | None:
    """«12», «12а», «12/1»: до 6 символов."""
    text = clean_text(value, 6)
    if text is None:
        return None
    text = text.lower()
    if not _APARTMENT.fullmatch(text):
        raise ValueError("Номер квартиры: цифры и при необходимости буква или дробь, например 12а")
    return text


def normalize_entrance(value: str | None) -> str | None:
    text = clean_text(value, 2)
    if text is None:
        return None
    if not re.fullmatch(r"\d{1,2}", text) or int(text) == 0:
        raise ValueError("Подъезд: число от 1 до 99")
    return str(int(text))


def _text_checker(max_len: int, min_len: int = 1, multiline: bool = False):
    def check(value: str | None) -> str | None:
        text = clean_text(value, max_len, multiline)
        if text is not None and len(text) < min_len:
            raise ValueError(f"Не короче {min_len} символов")
        return text

    return check


def Text(max_len: int, min_len: int = 1, multiline: bool = False):
    """Необязательная строка: trim, пустая -> None, без управляющих символов."""
    return Annotated[str | None, AfterValidator(_text_checker(max_len, min_len, multiline))]


def RequiredText(max_len: int, multiline: bool = False):
    """Обязательная строка: trim и те же проверки, но пустая недопустима."""

    def check(value: str) -> str:
        text = clean_text(value, max_len, multiline)
        if text is None:
            raise ValueError("Обязательное поле")
        return text

    return Annotated[str, AfterValidator(check)]


def _description(value: str) -> str:
    text = clean_text(value, 1000, multiline=True) or ""
    if text and len(text) < 5:
        raise ValueError("Опишите проблему подробнее: не короче 5 символов")
    return text


FullName = Annotated[str | None, AfterValidator(normalize_full_name)]
Phone = Annotated[str | None, AfterValidator(normalize_phone)]
Email = Annotated[str | None, AfterValidator(normalize_email)]
Apartment = Annotated[str | None, AfterValidator(normalize_apartment)]
Entrance = Annotated[str | None, AfterValidator(normalize_entrance)]
Description = Annotated[str, AfterValidator(_description)]
Reference = Annotated[str | None, AfterValidator(_text_checker(100))]
CustomAddress = Text(500, min_len=3)
CustomCompany = Text(300, min_len=3)
Place = Text(300)
ShortName = Text(200)
Unit = Text(20)
RequiredName = RequiredText(200)
ChatContent = RequiredText(4000, multiline=True)


def _reject_controls(value: str) -> str:
    if _has_control(value, multiline=False):
        raise ValueError("Недопустимые символы")
    return value


SearchQuery = Annotated[str, AfterValidator(_reject_controls)]


def _decimal_checker(low: str, high: str, places: int, what: str):
    low_d, high_d = Decimal(low), Decimal(high)

    def check(value: Decimal | None) -> Decimal | None:
        if value is None:
            return None
        if not value.is_finite():
            raise ValueError(f"{what}: нужно число")
        if not low_d <= value <= high_d:
            raise ValueError(f"{what}: от {low} до {high}")
        if -value.as_tuple().exponent > places:
            raise ValueError(f"{what}: не больше {places} знаков после запятой")
        return value

    return check


def _decimal_type(low: str, high: str, places: int, what: str, required: bool = False):
    check = AfterValidator(_decimal_checker(low, high, places, what))
    return Annotated[Decimal, check] if required else Annotated[Decimal | None, check]


MoneyAmount = _decimal_type("0", "1000000", 2, "Сумма")
RequiredMoney = _decimal_type("0", "1000000", 2, "Сумма", required=True)
SignedMoney = _decimal_type("-1000000", "1000000", 2, "Сумма", required=True)
VolumeAmount = _decimal_type("0", "100000", 3, "Объём")
TariffAmount = _decimal_type("0", "1000000", 4, "Тариф")
AreaAmount = _decimal_type("1", "1000", 2, "Площадь")


def _period(value: str) -> str:
    match = _PERIOD.fullmatch(value.strip())
    if not match:
        raise ValueError("Период в формате ГГГГ-ММ, например 2026-11")
    year, month = int(match[1]), int(match[2])
    today = date.today()
    last = (today.year + (today.month == 12), today.month % 12 + 1)
    if not FIRST_PERIOD <= (year, month) <= last:
        raise ValueError("Период: от 01.2020 до следующего месяца")
    return f"{year:04d}-{month:02d}"


Period = Annotated[str, AfterValidator(_period)]
