import uuid

from fastapi import APIRouter, UploadFile

from app.core.deps import ConsentedUser, CurrentUser, LLMDep, SessionDep
from app.core.rate_limit import LLMRateLimit
from app.core.region import get_region
from app.modules.receipts import analysis, letter, samples, service, tariffs
from app.modules.receipts import schemas as s

router = APIRouter(prefix="/receipts", tags=["receipts"])


@router.get("/samples", response_model=list[s.ReceiptSample])
async def list_samples() -> list[s.ReceiptSample]:
    """Демо-квитанции для знакомства с сервисом; без входа."""
    return samples.list_samples()


@router.get("/services", response_model=list[s.ServiceOption])
async def list_services(period: str = "") -> list[s.ServiceOption]:
    """Услуги для ручного ввода; на период (YYYY-MM) подставляется тариф региона, если он есть."""
    options = tariffs.service_options(get_region().tariffs, period)
    return [s.ServiceOption.model_validate(x) for x in options]


@router.post("/manual", response_model=s.Receipt, status_code=201, dependencies=[LLMRateLimit])
async def create_manual_receipt(
    data: s.ManualReceipt, user: ConsentedUser, session: SessionDep, llm: LLMDep
) -> s.Receipt:
    """Квитанция, введённая вручную; проверка и заявление на перерасчёт работают как обычно."""
    return service.to_schema(await service.create_manual(session, user.id, llm, data))


@router.post("", response_model=s.Receipt, status_code=201, dependencies=[LLMRateLimit])
async def upload_receipt(
    file: UploadFile, user: ConsentedUser, session: SessionDep, llm: LLMDep
) -> s.Receipt:
    """Фото или PDF квитанции (до 10 МБ). Без языковой модели отвечает 503."""
    data = await file.read(service.MAX_BYTES + 1)
    return service.to_schema(await service.upload(session, user.id, llm, data))


@router.post("/samples/{sample_id}", response_model=s.Receipt)
async def load_sample(
    sample_id: str, user: ConsentedUser, session: SessionDep, llm: LLMDep
) -> s.Receipt:
    return service.to_schema(await service.load_sample(session, user.id, llm, sample_id))


@router.get("", response_model=list[s.ReceiptShort])
async def list_receipts(user: CurrentUser, session: SessionDep) -> list[s.ReceiptShort]:
    found = await service.list_receipts(session, user.id)
    return [s.ReceiptShort.model_validate(r) for r in found]


@router.get("/compare", response_model=s.Compare)
async def compare_receipts(
    base: uuid.UUID, target: uuid.UUID, user: CurrentUser, session: SessionDep
) -> s.Compare:
    """Что изменилось между двумя квитанциями: по строкам, тарифу и объёму. Без модели, быстро."""
    return await analysis.compare(session, user.id, base, target)


@router.get(
    "/compare/explanation", response_model=s.CompareExplanation, dependencies=[LLMRateLimit]
)
async def compare_explanation(
    base: uuid.UUID, target: uuid.UUID, user: CurrentUser, session: SessionDep, llm: LLMDep
) -> s.CompareExplanation:
    """Пояснение к сравнению. Первый запрос может занять до минуты, затем берётся из кеша."""
    return await analysis.compare_explanation(session, user.id, llm, base, target)


@router.get("/{receipt_id}", response_model=s.Receipt)
async def get_receipt(receipt_id: uuid.UUID, user: CurrentUser, session: SessionDep) -> s.Receipt:
    return service.to_schema(await service.get_owned(session, user.id, receipt_id))


@router.patch("/{receipt_id}/lines/{line_id}", response_model=s.Receipt)
async def patch_line(
    receipt_id: uuid.UUID,
    line_id: int,
    data: s.LinePatch,
    user: ConsentedUser,
    session: SessionDep,
    llm: LLMDep,
) -> s.Receipt:
    """Исправление распознанных значений строки; итоги и предупреждения пересчитываются."""
    receipt = await service.patch_line(session, user.id, llm, receipt_id, line_id, data)
    return service.to_schema(receipt)


@router.get("/{receipt_id}/check", response_model=s.Check)
async def check_receipt(receipt_id: uuid.UUID, user: CurrentUser, session: SessionDep) -> s.Check:
    """Проверка начислений по тарифам региона: где возможна переплата."""
    receipt = await service.get_owned(session, user.id, receipt_id)
    return await analysis.check_receipt(session, user.id, receipt)


@router.post("/{receipt_id}/recalculation-letter", response_model=s.RecalculationLetter)
async def recalculation_letter(
    receipt_id: uuid.UUID,
    data: s.RecalculationLetterRequest,
    user: CurrentUser,
    session: SessionDep,
) -> s.RecalculationLetter:
    return await letter.build_letter(session, user, receipt_id, data.finding_types)
