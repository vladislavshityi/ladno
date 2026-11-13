import uuid
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import utcnow
from app.core.errors import Conflict, NotFound
from app.llm.client import LLMClient
from app.modules.houses import service as houses
from app.modules.houses.models import House, ManagementCompany
from app.modules.issues import drafts, photos, routing
from app.modules.issues.deadlines import add_deadline, is_overdue
from app.modules.issues.models import Issue, IssueStatus
from app.modules.issues.schemas import (
    Draft,
    IssueCreate,
    IssuePatch,
    IssuePhoto,
    IssueRead,
    RouteResult,
)
from app.modules.receipts import analysis
from app.modules.users.applicant import applicant_line
from app.modules.users.models import User


def to_read(issue: Issue) -> IssueRead:
    return IssueRead(
        id=issue.id,
        category=issue.category,
        category_title=drafts.category_title(issue.category),
        status=issue.status,
        house_id=issue.house_id,
        address=issue.house.address if issue.house else None,
        location_details=issue.location_details,
        photos=[
            IssuePhoto(id=uuid.UUID(p), url=photos.photo_url(uuid.UUID(p))) for p in issue.photo_ids
        ],
        route=RouteResult.model_validate(issue.route),
        escalation_level=issue.escalation_level,
        parent_issue_id=issue.parent_issue_id,
        draft=Draft(full=issue.draft_full, pos_short=issue.draft_pos_short),
        external_ref=issue.external_ref,
        submitted_at=issue.submitted_at,
        deadline_at=issue.deadline_at,
        is_overdue=is_overdue(utcnow(), issue.deadline_at, issue.status),
        created_at=issue.created_at,
    )


async def get_issue(session: AsyncSession, user_id: uuid.UUID, issue_id: uuid.UUID) -> Issue:
    issue = await session.get(Issue, issue_id)
    if issue is None or issue.user_id != user_id:
        raise NotFound("Обращение не найдено")
    return issue


async def list_issues(session: AsyncSession, user_id: uuid.UUID) -> list[IssueRead]:
    stmt = select(Issue).where(Issue.user_id == user_id).order_by(Issue.created_at.desc())
    found = list((await session.scalars(stmt)).all())
    return [to_read(i) for i in found]


def _company_for(user: User, house: House | None) -> ManagementCompany | None:
    """УК из профиля действует для дома из профиля; для другого дома берётся УК этого дома."""
    if house is None or house.id == user.house_id:
        return user.management_company or (house.management_company if house else None)
    return house.management_company


async def _issue_house(session: AsyncSession, user: User, house_id: int | None) -> House | None:
    if house_id is not None:
        return await houses.get_house(session, house_id)
    return user.house


async def create_issue(
    session: AsyncSession, user: User, llm: LLMClient | None, data: IssueCreate
) -> Issue:
    for photo_id in data.photo_ids:
        await photos.get_owned_photo(session, user.id, photo_id)
    house = await _issue_house(session, user, data.house_id)
    hint = await analysis.recalculation_hint(session, user.id)
    route = routing.build_route(
        data.category, data.answers, data.already_contacted_uk, _company_for(user, house), hint
    )
    summary = await drafts.build_summary(llm, data.category, data.answers)
    address = house.address if house else None
    draft = drafts.build_draft(
        summary, route, address, data.location_details, len(data.photo_ids), applicant_line(user)
    )
    issue = Issue(
        user_id=user.id,
        category=data.category,
        answers=data.answers,
        already_contacted_uk=data.already_contacted_uk,
        house_id=house.id if house else None,
        location_details=data.location_details,
        photo_ids=[str(p) for p in data.photo_ids],
        addressee_key=route.addressee.key,
        route=route.model_dump(mode="json"),
        summary=summary,
        draft_full=draft.full,
        draft_pos_short=draft.pos_short,
    )
    session.add(issue)
    await session.commit()
    await session.refresh(issue)
    return issue


def _mark_submitted(issue: Issue, submitted_at: datetime | None) -> None:
    issue.status = IssueStatus.SUBMITTED
    issue.submitted_at = submitted_at or utcnow()
    deadline = RouteResult.model_validate(issue.route).response_deadline
    issue.deadline_at = (
        add_deadline(issue.submitted_at, deadline.days, deadline.type) if deadline else None
    )


async def patch_issue(
    session: AsyncSession, user_id: uuid.UUID, issue_id: uuid.UUID, patch: IssuePatch
) -> Issue:
    issue = await get_issue(session, user_id, issue_id)
    if patch.draft is not None:
        issue.draft_full, issue.draft_pos_short = patch.draft.full, patch.draft.pos_short
    if "external_ref" in patch.model_fields_set:
        issue.external_ref = patch.external_ref
    if patch.status == IssueStatus.SUBMITTED and issue.status != IssueStatus.SUBMITTED:
        _mark_submitted(issue, patch.submitted_at)
    elif patch.status is not None:
        issue.status = patch.status
    await session.commit()
    return issue


def _previous(parent: Issue, route: RouteResult) -> dict:
    return {
        "addressee_name": route.addressee.name,
        "ref": parent.external_ref,
        "date": parent.submitted_at.strftime("%d.%m.%Y") if parent.submitted_at else None,
    }


async def escalate_issue(session: AsyncSession, user: User, issue_id: uuid.UUID) -> Issue:
    """Новое обращение на следующую ступень лестницы исходного."""
    parent = await get_issue(session, user.id, issue_id)
    parent_route = RouteResult.model_validate(parent.route)
    route = routing.build_escalated_route(parent_route, _company_for(user, parent.house))
    if route is None:
        raise Conflict("Дальше эскалировать некуда: ступени закончились", "no_escalation_left")
    address = parent.house.address if parent.house else None
    draft = drafts.build_escalation_draft(
        parent.summary, route, address, parent.location_details, len(parent.photo_ids),
        applicant_line(user), _previous(parent, parent_route),
    )  # fmt: skip
    issue = Issue(
        user_id=user.id,
        category=parent.category,
        answers=parent.answers,
        already_contacted_uk=parent.already_contacted_uk,
        house_id=parent.house_id,
        location_details=parent.location_details,
        photo_ids=parent.photo_ids,
        summary=parent.summary,
        parent_issue_id=parent.id,
        escalation_level=parent.escalation_level + 1,
        addressee_key=route.addressee.key,
        route=route.model_dump(mode="json"),
        draft_full=draft.full,
        draft_pos_short=draft.pos_short,
    )
    session.add(issue)
    await session.commit()
    await session.refresh(issue)
    return issue
