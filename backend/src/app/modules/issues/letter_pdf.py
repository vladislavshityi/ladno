"""PDF письма: текст обращения и фотографии на отдельных страницах."""

import asyncio
import io
import uuid
from dataclasses import dataclass
from datetime import datetime

from fpdf import FPDF
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.modules.issues import photos
from app.modules.issues.models import Issue

FONT = "DejaVu"
MARGIN = 20
LINE_HEIGHT = 6


@dataclass(frozen=True)
class PhotoFile:
    data: bytes
    content_type: str
    uploaded_at: datetime

    @property
    def extension(self) -> str:
        return self.content_type.removeprefix("image/").replace("jpeg", "jpg")


async def load_photos(session: AsyncSession, issue: Issue) -> list[PhotoFile]:
    """Фото обращения в порядке загрузки в мастере."""
    result = []
    for photo_id in issue.photo_ids:
        photo = await photos.get_owned_photo(session, issue.user_id, uuid.UUID(photo_id))
        data, content_type = await photos.read_photo(photo)
        result.append(PhotoFile(data, content_type, photo.created_at))
    return result


def _build(text: str, attachments: list[PhotoFile]) -> bytes:
    pdf = FPDF(format="A4")
    pdf.set_margins(MARGIN, MARGIN, MARGIN)
    pdf.add_font(FONT, fname=str(get_settings().fonts_dir / "DejaVuSans.ttf"))
    pdf.set_font(FONT, size=11)
    pdf.add_page()
    pdf.multi_cell(0, LINE_HEIGHT, text)
    for number, photo in enumerate(attachments, start=1):
        pdf.add_page()
        caption = f"Фото {number}, загружено {photo.uploaded_at:%d.%m.%Y}"
        pdf.cell(0, LINE_HEIGHT, caption, new_x="LMARGIN", new_y="NEXT")
        pdf.ln(2)
        box_width = pdf.w - 2 * MARGIN
        box_height = pdf.h - pdf.get_y() - MARGIN
        pdf.image(io.BytesIO(photo.data), w=box_width, h=box_height, keep_aspect_ratio=True)
    return bytes(pdf.output())


async def render_letter_pdf(issue: Issue, attachments: list[PhotoFile]) -> bytes:
    return await asyncio.to_thread(_build, issue.draft_full, attachments)
