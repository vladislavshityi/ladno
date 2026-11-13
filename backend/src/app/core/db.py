import uuid
from collections.abc import AsyncIterator
from datetime import UTC, datetime
from enum import Enum as PyEnum
from functools import lru_cache
from typing import Annotated

from sqlalchemy import DateTime, Enum, func
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase, mapped_column

from app.core.config import get_settings


def utcnow() -> datetime:
    return datetime.now(UTC)


UuidPk = Annotated[uuid.UUID, mapped_column(primary_key=True, default=uuid.uuid4)]
CreatedAt = Annotated[
    datetime,
    mapped_column(DateTime(timezone=True), default=utcnow, server_default=func.now()),
]


class Base(DeclarativeBase):
    pass


def str_enum[E: PyEnum](enum_class: type[E]) -> Enum:
    return Enum(
        enum_class,
        native_enum=False,
        length=24,
        create_constraint=False,
        values_callable=lambda e: [m.value for m in e],
    )


@lru_cache
def get_engine() -> AsyncEngine:
    return create_async_engine(get_settings().database_url, pool_pre_ping=True)


@lru_cache
def get_sessionmaker() -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(get_engine(), expire_on_commit=False)


async def get_session() -> AsyncIterator[AsyncSession]:
    async with get_sessionmaker()() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
