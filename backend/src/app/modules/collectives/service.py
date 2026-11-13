import uuid
from datetime import timedelta

from sqlalchemy import Select, distinct, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import utcnow
from app.core.errors import Conflict, NotFound, ValidationError
from app.modules.bot import service as bot
from app.modules.collectives.models import CollectiveIssue, CollectiveMember, CollectiveStatus
from app.modules.collectives.schemas import CollectiveRead, JoinRequest, SimilarIssues
from app.modules.houses.models import House
from app.modules.issues import drafts
from app.modules.issues import service as issues
from app.modules.issues.models import Issue, IssueStatus
from app.modules.users.models import User

# «Та же проблема»: тот же дом и категория, обращение не закрыто и подано не раньше месяца назад.
SIMILAR_STATUSES = (
    IssueStatus.DRAFT,
    IssueStatus.SUBMITTED,
    IssueStatus.IN_PROGRESS,
    IssueStatus.NO_RESPONSE,
)
SIMILAR_PERIOD = timedelta(days=30)
MIN_MEMBERS = 2


def _similar(*columns, house_id: int, category: str, user_id: uuid.UUID) -> Select:
    """Обращения других жителей о той же проблеме; место в доме (location_details) не важно."""
    return select(*columns).where(
        Issue.house_id == house_id,
        Issue.category == category,
        Issue.user_id != user_id,
        Issue.status.in_(SIMILAR_STATUSES),
        Issue.created_at >= utcnow() - SIMILAR_PERIOD,
    )


async def _open_collective(
    session: AsyncSession, house_id: int, category: str
) -> CollectiveIssue | None:
    stmt = (
        select(CollectiveIssue)
        .where(
            CollectiveIssue.house_id == house_id,
            CollectiveIssue.category == category,
            CollectiveIssue.status == CollectiveStatus.OPEN,
        )
        .order_by(CollectiveIssue.created_at.desc())
        .limit(1)
    )
    return await session.scalar(stmt)


async def find_similar(
    session: AsyncSession, user: User, house_id: int, category: str
) -> SimilarIssues:
    stmt = _similar(func.count(distinct(Issue.user_id)), house_id=house_id, category=category,
                    user_id=user.id)  # fmt: skip
    collective = await _open_collective(session, house_id, category)
    return SimilarIssues(
        count=await session.scalar(stmt) or 0, collective_id=collective.id if collective else None
    )


async def count_members(session: AsyncSession, collective_id: uuid.UUID) -> int:
    stmt = select(func.count()).where(CollectiveMember.collective_id == collective_id)
    return await session.scalar(stmt) or 0


async def get_membership(
    session: AsyncSession, user: User, collective_id: uuid.UUID
) -> tuple[CollectiveIssue, CollectiveMember]:
    """Коллектив виден только его участникам: чужой неотличим от несуществующего."""
    member = await session.get(CollectiveMember, (collective_id, user.id))
    collective = await session.get(CollectiveIssue, collective_id)
    if member is None or collective is None:
        raise NotFound("Коллективное обращение не найдено")
    return collective, member


async def to_read(
    session: AsyncSession, collective: CollectiveIssue, member: CollectiveMember
) -> CollectiveRead:
    house = await session.get(House, collective.house_id)
    return CollectiveRead(
        id=collective.id,
        house_id=collective.house_id,
        address=house.address,
        category=collective.category,
        category_title=drafts.category_title(collective.category),
        status=collective.status,
        members_count=await count_members(session, collective.id),
        my_issue_id=member.issue_id,
        consent_letter=member.consent_letter,
        created_at=collective.created_at,
        submitted_at=collective.submitted_at,
    )


async def _start(session: AsyncSession, issue: Issue) -> CollectiveIssue:
    """Новое коллективное обращение вокруг самого раннего похожего обращения соседа."""
    stmt = (
        _similar(Issue, house_id=issue.house_id, category=issue.category, user_id=issue.user_id)
        .where(Issue.collective_id.is_(None))
        .order_by(Issue.created_at)
        .limit(1)
    )
    initiator = await session.scalar(stmt)
    if initiator is None:
        raise Conflict("Похожих обращений соседей пока нет", "no_similar_issues")
    collective = CollectiveIssue(
        house_id=issue.house_id, category=issue.category, initiator_issue_id=initiator.id
    )
    session.add(collective)
    await session.flush()
    session.add(CollectiveMember(collective_id=collective.id, user_id=initiator.user_id,
                                 issue_id=initiator.id))  # fmt: skip
    initiator.collective_id = collective.id
    return collective


async def join(session: AsyncSession, user: User, data: JoinRequest) -> CollectiveRead:
    issue = await issues.get_issue(session, user.id, data.issue_id)
    if issue.house_id is None:
        raise ValidationError("Коллективное обращение возможно только для дома из справочника")
    collective = await _open_collective(session, issue.house_id, issue.category)
    already = collective and await session.get(CollectiveMember, (collective.id, user.id))
    if issue.collective_id is not None or already:
        raise Conflict("Вы уже участвуете в коллективном обращении", "already_joined")
    collective = collective or await _start(session, issue)

    member = CollectiveMember(collective_id=collective.id, user_id=user.id, issue_id=issue.id,
                              consent_letter=data.consent_letter)  # fmt: skip
    session.add(member)
    issue.collective_id = collective.id
    await session.flush()
    await _notify_initiator(session, collective)
    await session.commit()
    return await to_read(session, collective, member)


async def _notify_initiator(session: AsyncSession, collective: CollectiveIssue) -> None:
    initiator = collective.initiator_issue_id and await session.get(
        Issue, collective.initiator_issue_id
    )
    if initiator:
        count = await count_members(session, collective.id)
        text = f"К вашему обращению присоединился сосед. Теперь вас {count}."
        bot.add_notification(session, initiator.user_id, initiator.id, text)


async def update_consent(
    session: AsyncSession, user: User, collective_id: uuid.UUID, consent_letter: bool
) -> CollectiveRead:
    collective, member = await get_membership(session, user, collective_id)
    member.consent_letter = consent_letter
    await session.commit()
    return await to_read(session, collective, member)


async def submit(session: AsyncSession, user: User, collective_id: uuid.UUID) -> CollectiveRead:
    """Письмо подано: у черновиков участников стартует срок ответа, как у одиночных обращений."""
    collective, member = await get_membership(session, user, collective_id)
    if collective.status != CollectiveStatus.OPEN:
        raise Conflict("Коллективное обращение уже подано", "already_submitted")
    await require_enough_members(session, collective.id)
    drafts_of_members = await session.scalars(
        select(Issue).where(Issue.collective_id == collective.id, Issue.status == IssueStatus.DRAFT)
    )
    for issue in drafts_of_members:
        issues.mark_submitted(issue, None)
    collective.status = CollectiveStatus.SUBMITTED
    collective.submitted_at = utcnow()
    await session.commit()
    return await to_read(session, collective, member)


async def require_enough_members(session: AsyncSession, collective_id: uuid.UUID) -> None:
    if await count_members(session, collective_id) < MIN_MEMBERS:
        raise Conflict("Для коллективного письма нужно хотя бы два участника", "not_enough_members")
