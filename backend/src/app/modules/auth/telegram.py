"""Проверка подписи Telegram: Login Widget и Mini App (initData). Чистые функции, без IO."""

import hashlib
import hmac
import json
from collections.abc import Mapping
from dataclasses import dataclass
from urllib.parse import parse_qsl

MAX_CLOCK_SKEW_SECONDS = 300


class TelegramAuthError(Exception):
    """Подпись неверна или устарела; текст безопасно показывать пользователю."""


@dataclass(frozen=True)
class TelegramIdentity:
    telegram_id: int
    first_name: str | None


def _data_check_string(fields: Mapping[str, str]) -> str:
    return "\n".join(f"{key}={value}" for key, value in sorted(fields.items()))


def _signature(secret: bytes, fields: Mapping[str, str]) -> str:
    return hmac.new(secret, _data_check_string(fields).encode(), hashlib.sha256).hexdigest()


def _check_signature(secret: bytes, fields: Mapping[str, str], received: str) -> None:
    if not hmac.compare_digest(_signature(secret, fields), received):
        raise TelegramAuthError("Подпись Telegram неверна")


def _check_fresh(auth_date: str | None, now: float, max_age: int) -> None:
    try:
        issued = int(auth_date or "")
    except ValueError:
        raise TelegramAuthError("В данных Telegram нет времени входа") from None
    if now - issued > max_age or issued - now > MAX_CLOCK_SKEW_SECONDS:
        raise TelegramAuthError("Данные входа Telegram устарели")


def verify_widget(
    fields: Mapping[str, str], bot_token: str, now: float, max_age: int
) -> TelegramIdentity:
    """fields — все поля Login Widget, включая hash."""
    signed = {k: v for k, v in fields.items() if k != "hash"}
    secret = hashlib.sha256(bot_token.encode()).digest()
    _check_signature(secret, signed, fields.get("hash", ""))
    _check_fresh(signed.get("auth_date"), now, max_age)
    try:
        return TelegramIdentity(int(signed["id"]), signed.get("first_name"))
    except (KeyError, ValueError):
        raise TelegramAuthError("В данных Telegram нет пользователя") from None


def verify_webapp(init_data: str, bot_token: str, now: float, max_age: int) -> TelegramIdentity:
    pairs = dict(parse_qsl(init_data, keep_blank_values=True))
    received = pairs.pop("hash", "")
    secret = hmac.new(b"WebAppData", bot_token.encode(), hashlib.sha256).digest()
    _check_signature(secret, pairs, received)
    _check_fresh(pairs.get("auth_date"), now, max_age)
    return _webapp_user(pairs.get("user"))


def _webapp_user(user_json: str | None) -> TelegramIdentity:
    try:
        user = json.loads(user_json or "")
        return TelegramIdentity(int(user["id"]), user.get("first_name"))
    except (ValueError, KeyError, TypeError):
        raise TelegramAuthError("В данных Telegram нет пользователя") from None
