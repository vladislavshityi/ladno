import uuid

from fastapi import APIRouter, Response, status

from app.core.deps import BotAuth, SessionDep
from app.core.schemas import ErrorResponse
from app.modules.bot import service
from app.modules.bot.schemas import BotIssue, Reminder

router = APIRouter(
    prefix="/bot",
    tags=["bot"],
    dependencies=[BotAuth],
    responses={401: {"model": ErrorResponse, "description": "Неверный служебный токен бота"}},
)


@router.get("/users/{telegram_id}/issues", response_model=list[BotIssue])
async def list_user_issues(telegram_id: int, session: SessionDep) -> list[BotIssue]:
    """Последние обращения пользователя кратко: для команды «мои обращения»."""
    return await service.list_user_issues(session, telegram_id)


@router.get("/reminders", response_model=list[Reminder])
async def list_reminders(session: SessionDep) -> list[Reminder]:
    """Обращения, по которым пора напомнить о сроке ответа (за сутки и позже)."""
    return await service.due_reminders(session)


@router.post("/reminders/{issue_id}/sent", status_code=status.HTTP_204_NO_CONTENT)
async def mark_reminder_sent(issue_id: uuid.UUID, session: SessionDep) -> Response:
    """Бот отметил, что напоминание отправлено: повторно оно не придёт."""
    await service.mark_reminder_sent(session, issue_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
