import uuid

from fastapi import APIRouter

from app.core.deps import ConsentedUser, CurrentUser, SessionDep
from app.modules.issues import service as issues
from app.modules.submissions import service
from app.modules.submissions.schemas import ChannelRead, SendRequest, SendResponse

router = APIRouter(tags=["submissions"])


@router.get("/issues/{issue_id}/channels", response_model=list[ChannelRead])
async def list_channels(
    issue_id: uuid.UUID, user: CurrentUser, session: SessionDep
) -> list[ChannelRead]:
    """Способы подать обращение: всегда «сам», по email — если настроена почта и есть адрес."""
    return service.available_channels(await issues.get_issue(session, user.id, issue_id))


@router.post("/issues/{issue_id}/send", response_model=SendResponse)
async def send_issue(
    issue_id: uuid.UUID, data: SendRequest, user: ConsentedUser, session: SessionDep
) -> SendResponse:
    """Отправляет письмо с PDF и фото адресату; обращение становится поданным."""
    _, result = await service.send_issue(session, user, issue_id, data.channel)
    return SendResponse(
        channel=data.channel, external_ref=result.external_ref, message=result.message
    )
