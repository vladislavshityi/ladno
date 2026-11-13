"""Каналы отправки обращения: общий интерфейс, ручной канал и email."""

import asyncio
import smtplib
import ssl
from dataclasses import dataclass
from email.message import EmailMessage
from email.utils import make_msgid
from typing import Protocol

from app.core.config import get_settings
from app.modules.issues.drafts import category_title
from app.modules.issues.letter_pdf import PhotoFile
from app.modules.issues.models import Issue
from app.modules.issues.schemas import RouteResult

SMTP_TIMEOUT_SECONDS = 20


class SendError(Exception):
    """Канал не смог отправить; текст безопасен для журнала и ответа (без ПД)."""


@dataclass(frozen=True)
class SendResult:
    external_ref: str | None
    message: str


class SendChannel(Protocol):
    name: str
    label: str
    automatic: bool  # True: сервис отправляет сам, False: отправляет житель

    def recipient(self, issue: Issue) -> str | None: ...

    def available(self, issue: Issue) -> bool: ...

    async def send(
        self, issue: Issue, applicant_email: str | None, letter_pdf: bytes, photos: list[PhotoFile]
    ) -> SendResult: ...


class ManualChannel:
    """Житель сам подаёт текст через «Решаем вместе» или на сайте адресата."""

    name = "manual"
    label = "Подать самостоятельно"
    automatic = False

    def recipient(self, issue: Issue) -> str | None:
        return None

    def available(self, issue: Issue) -> bool:
        return True

    async def send(
        self, issue: Issue, applicant_email: str | None, letter_pdf: bytes, photos: list[PhotoFile]
    ) -> SendResult:
        return SendResult(None, "Подайте обращение сами и отметьте это в карточке")


class EmailChannel:
    """Письмо на почту адресата из справочника или карточки УК."""

    name = "email"
    label = "Отправить по email"
    automatic = True

    def recipient(self, issue: Issue) -> str | None:
        route = RouteResult.model_validate(issue.route)
        return next((c.value for c in route.addressee.channels if c.type == "email"), None)

    def available(self, issue: Issue) -> bool:
        return bool(get_settings().smtp_host and self.recipient(issue))

    async def send(
        self, issue: Issue, applicant_email: str | None, letter_pdf: bytes, photos: list[PhotoFile]
    ) -> SendResult:
        message = self._compose(issue, applicant_email, letter_pdf, photos)
        await asyncio.to_thread(self._deliver, message)
        return SendResult(message["Message-ID"], f"Письмо отправлено на {message['To']}")

    def _compose(
        self, issue: Issue, applicant_email: str | None, letter_pdf: bytes, photos: list[PhotoFile]
    ) -> EmailMessage:
        settings = get_settings()
        message = EmailMessage()
        message["From"] = settings.smtp_from or settings.smtp_user
        message["To"] = self.recipient(issue)
        message["Subject"] = f"Обращение жителя: {category_title(issue.category)}"
        message["Message-ID"] = make_msgid(domain="ladno")
        if applicant_email:
            message["Cc"] = applicant_email  # копия жителю
            message["Reply-To"] = applicant_email
        message.set_content(issue.draft_full)
        message.add_attachment(
            letter_pdf, maintype="application", subtype="pdf", filename="letter.pdf"
        )
        for number, photo in enumerate(photos, start=1):
            maintype, subtype = photo.content_type.split("/")
            message.add_attachment(
                photo.data, maintype=maintype, subtype=subtype,
                filename=f"photo-{number}.{photo.extension}",
            )  # fmt: skip
        return message

    def _deliver(self, message: EmailMessage) -> None:
        settings = get_settings()
        try:
            tls = ssl.create_default_context()
            if settings.smtp_tls == "ssl":
                server = smtplib.SMTP_SSL(
                    settings.smtp_host,
                    settings.smtp_port,
                    timeout=SMTP_TIMEOUT_SECONDS,
                    context=tls,
                )
            else:
                server = smtplib.SMTP(
                    settings.smtp_host, settings.smtp_port, timeout=SMTP_TIMEOUT_SECONDS
                )
            with server:
                if settings.smtp_tls == "starttls":
                    server.starttls(context=tls)
                if settings.smtp_user:
                    server.login(settings.smtp_user, settings.smtp_password)
                server.send_message(message)
        except (OSError, smtplib.SMTPException) as exc:
            # Текст SMTP-ошибки может содержать адреса, поэтому в журнал идёт только её тип.
            raise SendError(type(exc).__name__) from exc


CHANNELS: dict[str, SendChannel] = {c.name: c for c in (ManualChannel(), EmailChannel())}
