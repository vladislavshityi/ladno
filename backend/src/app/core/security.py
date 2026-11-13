import uuid
from datetime import timedelta

import jwt

from app.core.config import get_settings
from app.core.db import utcnow
from app.core.errors import Unauthorized


def create_access_token(user_id: uuid.UUID) -> str:
    settings = get_settings()
    expires = utcnow() + timedelta(minutes=settings.jwt_expire_minutes)
    payload = {"sub": str(user_id), "exp": expires}
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> uuid.UUID:
    settings = get_settings()
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
        return uuid.UUID(payload["sub"])
    except (jwt.PyJWTError, KeyError, ValueError) as exc:
        raise Unauthorized("Недействительный или просроченный токен", "invalid_token") from exc
