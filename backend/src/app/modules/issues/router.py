import uuid

from fastapi import APIRouter, Response

from app.core.deps import ConsentedUser, CurrentUser, LLMDep, SessionDep, quota
from app.core.quota import consume, grant_llm
from app.core.rate_limit import LLMRateLimit
from app.core.region import get_region
from app.modules.issues import classification, letter_pdf, photos, routing, service
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
    text = data.text.strip()
    if llm and not owned and (known := classification.cached(text)):
        return known  # тот же текст уже разбирала модель: лимит не тратим
    if llm:
        await consume(session, user.id, "classify")
        llm = await grant_llm(session, llm)
    images = [await photos.read_photo(p) for p in owned]
    return await classification.classify(llm, text, images)


@router.post("/issues/route", response_model=RouteResult)
async def get_route(data: RouteRequest, user: CurrentUser, session: SessionDep) -> RouteResult:
    """Адресат, основания, сроки и лестница эскалации по правилам региона."""
    hint = await analysis.recalculation_hint(session, user.id)
    place = await service.resolve_place(session, user, data.house_id, data.custom_address)
    return routing.build_route(
        data.category, data.answers, data.already_contacted_uk, place.company, hint
    )


@router.post("/issues", response_model=IssueRead, status_code=201, dependencies=[quota("issue")])
async def create_issue(
    data: IssueCreate, user: ConsentedUser, session: SessionDep, llm: LLMDep
) -> IssueRead:
    llm = await grant_llm(session, llm)
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


@router.post("/issues/{issue_id}/refresh-letter", response_model=IssueRead)
async def refresh_letter(
    issue_id: uuid.UUID, user: ConsentedUser, session: SessionDep
) -> IssueRead:
    """Пересобирает строку «От:» черновика из текущего профиля, без языковой модели."""
    return service.to_read(await service.refresh_letter(session, user, issue_id))


@router.get("/issues/{issue_id}/submission", response_model=Submission)
async def get_submission(issue_id: uuid.UUID, user: CurrentUser, session: SessionDep) -> Submission:
    """Всё для подачи вручную через «Решаем вместе»: текст, шаги, альтернативные каналы."""
    return build_submission(await service.get_issue(session, user.id, issue_id))


@router.get("/issues/{issue_id}/letter.pdf", response_class=Response)
async def get_letter_pdf(issue_id: uuid.UUID, user: CurrentUser, session: SessionDep) -> Response:
    """Письмо в PDF: полный текст и фото обращения, каждое на своей странице."""
    issue = await service.get_issue(session, user.id, issue_id)
    pdf = await letter_pdf.render_letter_pdf(issue, await letter_pdf.load_photos(session, issue))
    headers = {"Content-Disposition": 'attachment; filename="letter.pdf"'}
    return Response(pdf, media_type="application/pdf", headers=headers)


@router.post("/issues/{issue_id}/escalate", response_model=IssueRead, status_code=201)
async def escalate_issue(
    issue_id: uuid.UUID, user: ConsentedUser, session: SessionDep
) -> IssueRead:
    """Новое обращение на следующую ступень, если проблема не решена."""
    return service.to_read(await service.escalate_issue(session, user, issue_id))
