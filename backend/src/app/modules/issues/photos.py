import asyncio
import uuid
from pathlib import Path

from fastapi import APIRouter, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import files
from app.core.deps import ConsentedUser, CurrentUser, SessionDep
from app.core.errors import NotFound, PayloadTooLarge, UnsupportedMedia
from app.modules.issues.models import Photo
from app.modules.issues.schemas import PhotoRead

MAX_BYTES = 5 * 1024 * 1024
PHOTO_TYPES = ("image/jpeg", "image/png", "image/webp")

router = APIRouter(prefix="/photos", tags=["photos"])


def photo_url(photo_id: uuid.UUID) -> str:
    return f"/api/photos/{photo_id}"


async def save_photo(session: AsyncSession, user_id: uuid.UUID, data: bytes) -> Photo:
    if len(data) > MAX_BYTES:
        raise PayloadTooLarge("Файл больше 5 МБ")
    content_type = files.detect_content_type(data)
    if content_type not in PHOTO_TYPES:
        raise UnsupportedMedia("Нужен файл JPEG, PNG или WebP")
    path = await files.store_file(data, content_type, "photos")
    photo = Photo(user_id=user_id, path=str(path), content_type=content_type)
    session.add(photo)
    await session.commit()
    return photo


async def get_owned_photo(session: AsyncSession, user_id: uuid.UUID, photo_id: uuid.UUID) -> Photo:
    photo = await session.get(Photo, photo_id)
    if photo is None or photo.user_id != user_id:
        raise NotFound("Фото не найдено")
    return photo


async def read_photo(photo: Photo) -> tuple[bytes, str]:
    data = await asyncio.to_thread(Path(photo.path).read_bytes)
    return data, photo.content_type


async def delete_files_of(session: AsyncSession, user_id: uuid.UUID) -> None:
    paths = (await session.scalars(select(Photo.path).where(Photo.user_id == user_id))).all()
    await files.remove_files(list(paths))


@router.post("", response_model=PhotoRead, status_code=201)
async def upload_photo(file: UploadFile, user: ConsentedUser, session: SessionDep) -> PhotoRead:
    """Загрузка фото (JPEG, PNG, WebP до 5 МБ). Файл видит только владелец."""
    photo = await save_photo(session, user.id, await file.read(MAX_BYTES + 1))
    return PhotoRead(id=photo.id, url=photo_url(photo.id))


@router.get("/{photo_id}", response_class=FileResponse)
async def download_photo(
    photo_id: uuid.UUID, user: CurrentUser, session: SessionDep
) -> FileResponse:
    photo = await get_owned_photo(session, user.id, photo_id)
    return FileResponse(photo.path, media_type=photo.content_type)
