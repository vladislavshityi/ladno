"""Загруженные файлы: тип по сигнатуре, а не по заявленному MIME, и хранение на диске."""

import asyncio
import io
import secrets
from pathlib import Path

from PIL import Image, ImageOps, UnidentifiedImageError

from app.core.config import get_settings
from app.core.errors import UnsupportedMedia

# Файл до 5 МБ может распаковаться в гигабайты («бомба»): картинки крупнее не разбираем.
MAX_PIXELS = 50_000_000

EXTENSIONS = {
    "image/jpeg": "jpg",
    "image/png": "png",
    "image/webp": "webp",
    "application/pdf": "pdf",
}


def detect_content_type(data: bytes) -> str | None:
    if data.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "image/webp"
    if data.startswith(b"%PDF-"):
        return "application/pdf"
    return None


def strip_metadata(data: bytes, content_type: str) -> bytes:
    """Пересохраняет картинку без EXIF: в нём бывают координаты съёмки и модель телефона."""
    out = io.BytesIO()
    try:
        with Image.open(io.BytesIO(data)) as image:
            if image.width * image.height > MAX_PIXELS:
                raise UnsupportedMedia("Изображение слишком большое по размерам")
            clean = ImageOps.exif_transpose(image)
            clean.save(out, format=EXTENSIONS[content_type].replace("jpg", "jpeg"), quality=90)
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError) as error:
        raise UnsupportedMedia("Не удалось прочитать изображение") from error
    return out.getvalue()


async def store_file(data: bytes, content_type: str, subdir: str) -> Path:
    """Сохраняет файл под случайным именем: исходное имя пользователя не используется."""
    directory = get_settings().upload_dir / subdir
    path = directory / f"{secrets.token_hex(16)}.{EXTENSIONS[content_type]}"

    def write() -> None:
        directory.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)

    await asyncio.to_thread(write)
    return path


async def remove_files(paths: list[str]) -> None:
    await asyncio.to_thread(lambda: [Path(p).unlink(missing_ok=True) for p in paths])
