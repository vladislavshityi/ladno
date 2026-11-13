import logging
import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.errors import BadGateway, Conflict, NotFound, TooManyRequests
from app.modules.issues import letter_pdf
from app.modules.issues import service as issues
from app.modules.issues.models import Issue, IssueStatus
from app.modules.submissions.channels import CHANNELS, SendError, SendResult
from app.modules.submissions.models import AttemptStatus, SubmissionAttempt
from app.modules.submissions.schemas import ChannelRead
from app.modules.users.models import User

log = logging.getLogger(__name__)


def available_channels(issue: Issue) -> list[ChannelRead]:
    return [
        ChannelRead(name=c.name, label=c.label, automatic=c.automatic, recipient=c.recipient(issue))
        for c in CHANNELS.values()
        if c.available(issue)
    ]


async def _sent_count(session: AsyncSession, issue_id: uuid.UUID, channel: str) -> int:
    stmt = select(func.count()).where(
        SubmissionAttempt.issue_id == issue_id,
        SubmissionAttempt.channel == channel,
        SubmissionAttempt.status == AttemptStatus.SENT,
    )
    return await session.scalar(stmt) or 0


async def send_issue(
    session: AsyncSession, user: User, issue_id: uuid.UUID, channel_name: str
) -> tuple[Issue, SendResult]:
    issue = await issues.get_issue(session, user.id, issue_id)
    channel = CHANNELS.get(channel_name)
    if channel is None or not channel.available(issue):
        raise NotFound("Этот способ отправки недоступен для обращения", "channel_unavailable")
    if not channel.automatic:
        raise Conflict("Это обращение подаёт сам житель", "manual_channel")
    if issue.status not in (IssueStatus.DRAFT, IssueStatus.SUBMITTED):
        raise Conflict("Обращение уже в работе или закрыто", "issue_not_sendable")
    if await _sent_count(session, issue.id, channel.name) >= get_settings().email_sends_per_issue:
        raise TooManyRequests(
            "Обращение уже отправлено несколько раз, повторять не нужно", "send_limit_reached"
        )

    attachments = await letter_pdf.load_photos(session, issue)
    pdf = await letter_pdf.render_letter_pdf(issue, attachments)
    try:
        result = await channel.send(issue, user.email, pdf, attachments)
    except SendError as exc:
        log.warning(
            "Отправка обращения %s по каналу %s не удалась: %s", issue.id, channel.name, exc
        )
        session.add(
            SubmissionAttempt(
                issue_id=issue.id, channel=channel.name, status=AttemptStatus.FAILED, error=str(exc)
            )
        )
        await session.commit()
        raise BadGateway(
            "Не удалось отправить письмо. Попробуйте позже или отправьте обращение сами",
            "send_failed",
        ) from exc

    session.add(
        SubmissionAttempt(
            issue_id=issue.id,
            channel=channel.name,
            status=AttemptStatus.SENT,
            external_ref=result.external_ref,
        )
    )
    if issue.status == IssueStatus.DRAFT:
        issues.mark_submitted(issue, None)
    issue.external_ref = result.external_ref
    await session.commit()
    return issue, result
