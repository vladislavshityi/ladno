import uuid

from fastapi import APIRouter, Response

from app.core.deps import ConsentedUser, CurrentUser, SessionDep
from app.modules.collectives import letter, service
from app.modules.collectives.schemas import (
    CollectiveLetter,
    CollectiveRead,
    JoinRequest,
    MembershipPatch,
    SimilarIssues,
)

router = APIRouter(tags=["collectives"])


@router.get("/issues/similar", response_model=SimilarIssues)
async def get_similar(
    house_id: int, category: str, user: CurrentUser, session: SessionDep
) -> SimilarIssues:
    """Сколько соседей по дому за последний месяц сообщили о такой же проблеме."""
    return await service.find_similar(session, user, house_id, category)


@router.post("/collectives/join", response_model=CollectiveRead, status_code=201)
async def join_collective(
    data: JoinRequest, user: ConsentedUser, session: SessionDep
) -> CollectiveRead:
    """Присоединяет обращение к коллективному по тому же дому и категории; если его ещё нет,
    создаёт вокруг самого раннего похожего обращения соседа."""
    return await service.join(session, user, data)


@router.get("/collectives/{collective_id}", response_model=CollectiveRead)
async def get_collective(
    collective_id: uuid.UUID, user: CurrentUser, session: SessionDep
) -> CollectiveRead:
    collective, member = await service.get_membership(session, user, collective_id)
    return await service.to_read(session, collective, member)


@router.patch("/collectives/{collective_id}/membership", response_model=CollectiveRead)
async def update_membership(
    collective_id: uuid.UUID, data: MembershipPatch, user: ConsentedUser, session: SessionDep
) -> CollectiveRead:
    """Согласие или отказ указывать свои ФИО и квартиру в коллективном письме."""
    return await service.update_consent(session, user, collective_id, data.consent_letter)


@router.post("/collectives/{collective_id}/letter", response_model=CollectiveLetter)
async def build_collective_letter(
    collective_id: uuid.UUID, user: CurrentUser, session: SessionDep
) -> CollectiveLetter:
    """Текст коллективного письма по шаблону; нужно не меньше двух участников."""
    collective, _ = await service.get_membership(session, user, collective_id)
    await service.require_enough_members(session, collective.id)
    return await letter.build_letter(session, collective)


@router.get("/collectives/{collective_id}/letter.pdf", response_class=Response)
async def get_collective_letter_pdf(
    collective_id: uuid.UUID, user: CurrentUser, session: SessionDep
) -> Response:
    """Коллективное письмо в PDF: текст и фото всех участников."""
    collective, _ = await service.get_membership(session, user, collective_id)
    await service.require_enough_members(session, collective.id)
    text = (await letter.build_letter(session, collective)).text
    pdf = await letter.render_pdf(session, collective, text)
    headers = {"Content-Disposition": 'attachment; filename="collective-letter.pdf"'}
    return Response(pdf, media_type="application/pdf", headers=headers)


@router.post("/collectives/{collective_id}/submit", response_model=CollectiveRead)
async def submit_collective(
    collective_id: uuid.UUID, user: ConsentedUser, session: SessionDep
) -> CollectiveRead:
    """Отмечает письмо поданным: у обращений-черновиков участников начинается срок ответа."""
    return await service.submit(session, user, collective_id)
