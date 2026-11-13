import re
import uuid
from dataclasses import dataclass
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
from app.modules.issues.models import ANSWERED_STATUSES, Issue, IssueStatus
from app.modules.issues.schemas import (
    Draft,
    IssueCreate,
    IssuePatch,
    IssuePhoto,
    IssueRead,
    RouteResult,
)
from app.modules.receipts import analysis
from app.modules.users.applicant import applicant_line, missing_fields
from app.modules.users.models import User


def to_read(issue: Issue) -> IssueRead:
    return IssueRead(
        id=issue.id,
        category=issue.category,
        category_title=drafts.category_title(issue.category),
        status=issue.status,
        house_id=issue.house_id,
        address=issue.house.address if issue.house else issue.custom_address,
        location_details=issue.location_details,
        description=issue.description,
        photos=[
            IssuePhoto(id=uuid.UUID(p), url=photos.photo_url(uuid.UUID(p))) for p in issue.photo_ids
        ],
        route=RouteResult.model_validate(issue.route),
        escalation_level=issue.escalation_level,
        parent_issue_id=issue.parent_issue_id,
        draft=Draft(full=issue.draft_full, pos_short=issue.draft_pos_short),
        missing_applicant_fields=missing_fields(issue.draft_full),
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


@dataclass(frozen=True)
class Place:
    house: House | None
    address: str | None
    company: ManagementCompany | None


def _profile_company(user: User) -> ManagementCompany | None:
    if user.management_company:
        return user.management_company
    return routing.custom_company(user.custom_company_name) if user.custom_company_name else None


async def resolve_place(
    session: AsyncSession, user: User, house_id: int | None, custom_address: str | None
) -> Place:
    """Дом (из справочника или введённый вручную) и УК для него.

    Без дома в запросе берётся дом из профиля. УК из профиля действует только для места из
    профиля; для другого дома берётся УК этого дома, для другого введённого адреса УК неизвестна.
    """
    if house_id is None and not custom_address:
        house_id, custom_address = user.house_id, user.custom_address
    house = await houses.get_house(session, house_id) if house_id is not None else None
    own = (house_id, custom_address) == (user.house_id, user.custom_address)
    company = (_profile_company(user) if own else None) or (
        house.management_company if house else None
    )
    return Place(house, house.address if house else custom_address, company)


async def create_issue(
    session: AsyncSession, user: User, llm: LLMClient | None, data: IssueCreate
) -> Issue:
    for photo_id in data.photo_ids:
        await photos.get_owned_photo(session, user.id, photo_id)
    place = await resolve_place(session, user, data.house_id, data.custom_address)
    hint = await analysis.recalculation_hint(session, user.id)
    route = routing.build_route(
        data.category, data.answers, data.already_contacted_uk, place.company, hint
    )
    summary = await drafts.build_summary(
        llm, data.category, data.answers, route.addressee, data.description
    )
    draft = drafts.build_draft(
        summary,
        route,
        place.address,
        data.location_details,
        len(data.photo_ids),
        applicant_line(user),
    )
    issue = Issue(
        user_id=user.id,
        category=data.category,
        answers=data.answers,
        already_contacted_uk=data.already_contacted_uk,
        house_id=place.house.id if place.house else None,
        custom_address=None if place.house else place.address,
        location_details=data.location_details,
        description=data.description.strip(),
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


def mark_submitted(issue: Issue, submitted_at: datetime | None) -> None:
    issue.status = IssueStatus.SUBMITTED
    issue.answered_at = None
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
        mark_submitted(issue, patch.submitted_at)
    elif patch.status is not None:
        issue.status = patch.status
        if patch.status not in ANSWERED_STATUSES:
            issue.answered_at = None
        elif issue.answered_at is None:
            issue.answered_at = utcnow()
    await session.commit()
    return issue


async def refresh_letter(session: AsyncSession, user: User, issue_id: uuid.UUID) -> Issue:
    """Подставляет в строку «От:» текущие данные профиля; правки текста письма не трогает."""
    issue = await get_issue(session, user.id, issue_id)
    if issue.status != IssueStatus.DRAFT:
        raise Conflict("Письмо можно обновить только в черновике", "not_a_draft")
    issue.draft_full = re.sub(
        r"^От: .*$", lambda _: f"От: {applicant_line(user)}", issue.draft_full, count=1, flags=re.M
    )
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
    place = await resolve_place(session, user, parent.house_id, parent.custom_address)
    route = routing.build_escalated_route(parent_route, place.company)
    if route is None:
        raise Conflict("Дальше эскалировать некуда: ступени закончились", "no_escalation_left")
    summary = parent.summary
    if not drafts.summary_fits(summary, route.addressee.key):
        summary = await drafts.build_summary(
            None, parent.category, parent.answers, route.addressee, parent.description
        )
    draft = drafts.build_escalation_draft(
        summary, route, place.address, parent.location_details, len(parent.photo_ids),
        applicant_line(user), _previous(parent, parent_route),
    )  # fmt: skip
    issue = Issue(
        user_id=user.id,
        category=parent.category,
        answers=parent.answers,
        already_contacted_uk=parent.already_contacted_uk,
        house_id=parent.house_id,
        custom_address=parent.custom_address,
        location_details=parent.location_details,
        photo_ids=parent.photo_ids,
        summary=summary,
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
