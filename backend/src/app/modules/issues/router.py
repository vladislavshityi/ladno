import uuid

from fastapi import APIRouter

from app.core.deps import ConsentedUser, CurrentUser, LLMDep, SessionDep
from app.core.rate_limit import LLMRateLimit
from app.core.region import get_region
from app.modules.issues import classification, photos, routing, service
from app.modules.issues.schemas import (
    Category,
    Classification,
    ClassifyRequest,
    IssueCreate,
    IssuePatch,
    IssueRead,
    Question,
    RouteRequest,
    RouteResult,
    Submission,
)
from app.modules.issues.submission import build_submission
from app.modules.receipts import analysis

router = APIRouter(tags=["issues"])


@router.get("/categories", response_model=list[Category])
async def list_categories() -> list[Category]:
    """Категории проблем региона."""
    return [Category.model_validate(c) for c in get_region().categories]


@router.get("/categories/{category_id}/questions", response_model=list[Question])
async def list_questions(category_id: str) -> list[Question]:
    """Уточняющие вопросы категории: от ответов зависит адресат и срок."""
    return routing.get_questions(category_id)


@router.post("/issues/classify", response_model=Classification, dependencies=[LLMRateLimit])
async def classify(
    data: ClassifyRequest, user: CurrentUser, session: SessionDep, llm: LLMDep
) -> Classification:
    """Категория по описанию и фото. Без модели или при сомнении — needs_manual_choice."""
    owned = [await photos.get_owned_photo(session, user.id, p) for p in data.photo_ids]
    images = [await photos.read_photo(p) for p in owned]
    return await classification.classify(llm, data.text.strip(), images)


@router.post("/issues/route", response_model=RouteResult)
async def get_route(data: RouteRequest, user: CurrentUser, session: SessionDep) -> RouteResult:
    """Адресат, основания, сроки и лестница эскалации по правилам региона."""
    hint = await analysis.recalculation_hint(session, user.id)
    company = user.management_company
    return routing.build_route(
        data.category, data.answers, data.already_contacted_uk, company, hint
    )


@router.post("/issues", response_model=IssueRead, status_code=201)
async def create_issue(
    data: IssueCreate, user: ConsentedUser, session: SessionDep, llm: LLMDep
) -> IssueRead:
    return service.to_read(await service.create_issue(session, user, llm, data))


@router.get("/issues", response_model=list[IssueRead])
async def list_issues(user: CurrentUser, session: SessionDep) -> list[IssueRead]:
    return await service.list_issues(session, user.id)


@router.get("/issues/{issue_id}", response_model=IssueRead)
async def get_issue(issue_id: uuid.UUID, user: CurrentUser, session: SessionDep) -> IssueRead:
    return service.to_read(await service.get_issue(session, user.id, issue_id))


@router.patch("/issues/{issue_id}", response_model=IssueRead)
async def patch_issue(
    issue_id: uuid.UUID, data: IssuePatch, user: ConsentedUser, session: SessionDep
) -> IssueRead:
    """Правка черновика, номера обращения и статуса. Статус submitted запускает отсчёт срока."""
    issue = await service.patch_issue(session, user.id, issue_id, data)
    return service.to_read(issue)


@router.get("/issues/{issue_id}/submission", response_model=Submission)
async def get_submission(issue_id: uuid.UUID, user: CurrentUser, session: SessionDep) -> Submission:
    """Всё для подачи вручную через «Решаем вместе»: текст, шаги, альтернативные каналы."""
    return build_submission(await service.get_issue(session, user.id, issue_id))


@router.post("/issues/{issue_id}/escalate", response_model=IssueRead, status_code=201)
async def escalate_issue(
    issue_id: uuid.UUID, user: ConsentedUser, session: SessionDep
) -> IssueRead:
    """Новое обращение на следующую ступень, если проблема не решена."""
    return service.to_read(await service.escalate_issue(session, user, issue_id))
