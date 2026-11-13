import hashlib
import hmac
import json
from urllib.parse import urlencode

import pytest

from app.modules.auth.telegram import TelegramAuthError, verify_webapp, verify_widget

TOKEN = "123456:TEST-TOKEN"
NOW = 1_800_000_000
MAX_AGE = 86400


def sign_widget(fields: dict[str, str], token: str = TOKEN) -> dict[str, str]:
    check = "\n".join(f"{k}={v}" for k, v in sorted(fields.items()))
    secret = hashlib.sha256(token.encode()).digest()
    digest = hmac.new(secret, check.encode(), hashlib.sha256).hexdigest()
    return {**fields, "hash": digest}


def sign_webapp(fields: dict[str, str], token: str = TOKEN) -> str:
    check = "\n".join(f"{k}={v}" for k, v in sorted(fields.items()))
    secret = hmac.new(b"WebAppData", token.encode(), hashlib.sha256).digest()
    digest = hmac.new(secret, check.encode(), hashlib.sha256).hexdigest()
    return urlencode({**fields, "hash": digest})


def widget_fields(**over: str) -> dict[str, str]:
    base = {"id": "42", "first_name": "Анна", "auth_date": str(NOW - 60)}
    return {**base, **over}


def webapp_fields(**over: str) -> dict[str, str]:
    user = json.dumps({"id": 42, "first_name": "Анна", "username": "anna"}, ensure_ascii=False)
    return {"auth_date": str(NOW - 60), "query_id": "q1", "user": user, **over}


def test_widget_valid():
    identity = verify_widget(sign_widget(widget_fields()), TOKEN, NOW, MAX_AGE)
    assert (identity.telegram_id, identity.first_name) == (42, "Анна")


def test_widget_tampered_field():
    data = sign_widget(widget_fields())
    data["id"] = "43"
    with pytest.raises(TelegramAuthError, match="неверна"):
        verify_widget(data, TOKEN, NOW, MAX_AGE)


def test_widget_wrong_token_and_missing_hash():
    with pytest.raises(TelegramAuthError):
        verify_widget(sign_widget(widget_fields(), "other:token"), TOKEN, NOW, MAX_AGE)
    with pytest.raises(TelegramAuthError):
        verify_widget(widget_fields(), TOKEN, NOW, MAX_AGE)


def test_widget_expired_and_from_future():
    old = sign_widget(widget_fields(auth_date=str(NOW - MAX_AGE - 1)))
    with pytest.raises(TelegramAuthError, match="устарели"):
        verify_widget(old, TOKEN, NOW, MAX_AGE)
    future = sign_widget(widget_fields(auth_date=str(NOW + 3600)))
    with pytest.raises(TelegramAuthError, match="устарели"):
        verify_widget(future, TOKEN, NOW, MAX_AGE)


def test_webapp_valid():
    identity = verify_webapp(sign_webapp(webapp_fields()), TOKEN, NOW, MAX_AGE)
    assert (identity.telegram_id, identity.first_name) == (42, "Анна")


def test_webapp_tampered_user():
    signed = sign_webapp(webapp_fields())
    forged = signed.replace("%22id%22%3A+42", "%22id%22%3A+7")
    assert forged != signed
    with pytest.raises(TelegramAuthError, match="неверна"):
        verify_webapp(forged, TOKEN, NOW, MAX_AGE)


def test_webapp_signed_with_widget_scheme_is_rejected():
    data = sign_widget(webapp_fields())
    with pytest.raises(TelegramAuthError):
        verify_webapp(urlencode(data), TOKEN, NOW, MAX_AGE)


def test_webapp_expired_and_no_user():
    old = sign_webapp(webapp_fields(auth_date=str(NOW - MAX_AGE - 1)))
    with pytest.raises(TelegramAuthError, match="устарели"):
        verify_webapp(old, TOKEN, NOW, MAX_AGE)
    without_user = webapp_fields()
    del without_user["user"]
    with pytest.raises(TelegramAuthError, match="нет пользователя"):
        verify_webapp(sign_webapp(without_user), TOKEN, NOW, MAX_AGE)
