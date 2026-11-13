from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.db import utcnow
from app.core.errors import Conflict
from app.modules.houses import service as houses
from app.modules.issues import photos
from app.modules.issues import service as issues
from app.modules.issues.models import Photo
from app.modules.issues.schemas import PhotoRead
from app.modules.receipts import service as receipts
from app.modules.users.models import User
from app.modules.users.schemas import ProfileUpdate, UserExport, UserRead


def to_read(user: User) -> UserRead:
    current = get_settings().consent_version
    read = UserRead.model_validate(user)
    read.consent_required = user.consent_version != current
    company = read.management_company
    house_company = read.house.management_company if read.house else None
    if company and house_company and company.id == house_company.id:
        company.source = house_company.source
    return read


async def update_profile(session: AsyncSession, user: User, data: ProfileUpdate) -> User:
    house = await houses.get_house(session, data.house_id) if data.house_id else None
    company_id = data.management_company_id
    if company_id is not None:
        await houses.get_company(session, company_id)
    elif house is not None and not data.custom_company_name:
        company_id = house.management_company_id
    user.house, user.entrance = house, data.entrance
    user.custom_address, user.custom_company_name = data.custom_address, data.custom_company_name
    user.full_name, user.phone = data.full_name, data.phone
    user.email, user.apartment = data.email, data.apartment
    user.management_company_id = company_id
    await session.commit()
    await session.refresh(user)
    return user


async def accept_consent(session: AsyncSession, user: User, version: str) -> User:
    current = get_settings().consent_version
    if version != current:
        raise Conflict(f"Актуальная версия согласия: {current}", "consent_version_mismatch")
    user.consent_version, user.consent_at = version, utcnow()
    await session.commit()
    return user


async def delete_account(session: AsyncSession, user: User) -> None:
    """Удаляет пользователя вместе с обращениями, квитанциями и файлами фото."""
    await photos.delete_files_of(session, user.id)
    await session.delete(user)
    await session.commit()


async def export_data(session: AsyncSession, user: User) -> UserExport:
    """Все данные пользователя: профиль, обращения с черновиками, квитанции, фото."""
    photo_ids = (await session.scalars(select(Photo.id).where(Photo.user_id == user.id))).all()
    return UserExport(
        profile=to_read(user),
        issues=await issues.list_issues(session, user.id),
        receipts=[receipts.to_schema(r) for r in await receipts.list_receipts(session, user.id)],
        photos=[PhotoRead(id=i, url=photos.photo_url(i)) for i in photo_ids],
    )
