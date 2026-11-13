"""Шифрование персональных данных в БД: ФИО, телефон, email и адрес хранятся как шифротекст."""

from functools import lru_cache

from cryptography.fernet import Fernet
from sqlalchemy import Text
from sqlalchemy.types import TypeDecorator

from app.core.config import get_settings


@lru_cache
def _fernet() -> Fernet:
    return Fernet(get_settings().pii_encryption_key.encode())


class EncryptedString(TypeDecorator[str]):
    """Строка, которая шифруется при записи и расшифровывается при чтении."""

    impl = Text
    cache_ok = True

    def process_bind_param(self, value: str | None, dialect: object) -> str | None:
        return None if value is None else _fernet().encrypt(value.encode()).decode()

    def process_result_value(self, value: str | None, dialect: object) -> str | None:
        return None if value is None else _fernet().decrypt(value.encode()).decode()
