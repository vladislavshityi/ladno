import re
import uuid
from decimal import Decimal

from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import files
from app.core.db import utcnow
from app.core.errors import (
    BadGateway,
    NotFound,
    PayloadTooLarge,
    ServiceUnavailable,
    UnsupportedMedia,
)
from app.llm.client import LLMClient
from app.modules.receipts import explain, samples, schemas
from app.modules.receipts import parsing as llm_parsing
from app.modules.receipts.calc import ZERO, LineData, ReceiptData
from app.modules.receipts.models import Receipt, ReceiptLine
from app.modules.receipts.overcharge import accrual_mismatch, sum_mismatch
from app.modules.receipts.schemas import LinePatch, ParsedLine, ParsedReceipt
from app.modules.receipts.schemas import ReceiptLine as ReceiptLineSchema
from app.modules.receipts.tariffs import PERIOD_RE

MAX_BYTES = 10 * 1024 * 1024
RECEIPT_TYPES = ("image/jpeg", "image/png", "application/pdf")


def line_data(line: ReceiptLine | ParsedLine) -> LineData:
    """Строка квитанции для расчётов в чистых функциях."""
    return LineData(
        service_code=line.service_code,
        service_name=line.service_name,
        accrued=line.accrued,
        recalculation=line.recalculation,
        volume=line.volume,
        tariff=line.tariff,
        method=line.method,
    )


def receipt_data(receipt: Receipt) -> ReceiptData:
    lines = tuple(line_data(x) for x in receipt.lines)
    return ReceiptData(period=receipt.period or "", total=receipt.total, lines=lines)


def to_schema(receipt: Receipt) -> schemas.Receipt:
    company = (
        schemas.ReceiptCompany(name=receipt.uk_name, inn=receipt.uk_inn)
        if receipt.uk_name
        else None
    )
    return schemas.Receipt(
        id=receipt.id,
        status=receipt.status,
        period=receipt.period,
        management_company=company,
        account_last4=receipt.account_last4,
        area_m2=receipt.area_m2,
        residents=receipt.residents,
        lines=[schemas.ReceiptLine.model_validate(x) for x in receipt.lines],
        total=receipt.total,
        warnings=receipt.warnings,
    )


def _last4(account: str | None) -> str | None:
    """Лицевой счёт хранится только маской: последние 4 цифры."""
    return re.sub(r"\D", "", account or "")[-4:] or None


def _warnings(period: str | None, lines: list[LineData], total: Decimal) -> list[str]:
    warnings = []
    if not period:
        warnings.append("Не распознан период квитанции.")
    if not lines:
        warnings.append("Не удалось распознать строки квитанции.")
    warnings += [
        f"«{x.service_name}»: начислено не совпадает с объёмом × тариф."
        for x in lines
        if accrual_mismatch(x)
    ]
    if lines and sum_mismatch(ReceiptData(period or "", total, tuple(lines))):
        warnings.append("Сумма строк не совпадает с итогом квитанции.")
    return warnings


def _row(line: ParsedLine) -> ReceiptLine:
    total = line.total if line.total is not None else line.accrued + line.recalculation
    return ReceiptLine(**line.model_dump(exclude={"total"}), total=total)


def _build(user_id: uuid.UUID, parsed: ParsedReceipt, sample_id: str | None) -> Receipt:
    period = parsed.period if parsed.period and PERIOD_RE.match(parsed.period) else None
    lines = [_row(x) for x in parsed.lines]
    total = parsed.total if parsed.total is not None else sum((x.total for x in lines), ZERO)
    warnings = _warnings(period, [line_data(x) for x in lines], total)
    company = parsed.management_company
    return Receipt(
        user_id=user_id,
        period=period,
        uk_name=company.name if company else None,
        uk_inn=company.inn if company else None,
        account_last4=_last4(parsed.account_last4),
        area_m2=parsed.area_m2,
        residents=parsed.residents,
        total=total,
        status="needs_review" if warnings else "parsed",
        warnings=warnings,
        sample_id=sample_id,
        lines=lines,
    )


async def _explain(
    llm: LLMClient | None, receipt: Receipt, only_line_id: int | None = None
) -> None:
    lines = [ReceiptLineSchema.model_validate(x) for x in receipt.lines]
    texts = await explain.explain_lines(llm, lines)
    for line in receipt.lines:
        if only_line_id in (None, line.id):
            line.explanation = texts[line.id]


async def _store(
    session: AsyncSession,
    user_id: uuid.UUID,
    llm: LLMClient | None,
    parsed: ParsedReceipt,
    sample_id: str | None = None,
) -> Receipt:
    receipt = _build(user_id, parsed, sample_id)
    session.add(receipt)
    await session.flush()  # у строк появятся id для объяснений
    await _explain(llm, receipt)
    await session.commit()
    return receipt


async def upload(
    session: AsyncSession, user_id: uuid.UUID, llm: LLMClient | None, data: bytes
) -> Receipt:
    """Разбор фото или PDF квитанции моделью; сам файл на сервере не хранится."""
    if len(data) > MAX_BYTES:
        raise PayloadTooLarge("Файл больше 10 МБ")
    content_type = files.detect_content_type(data)
    if content_type not in RECEIPT_TYPES:
        raise UnsupportedMedia("Нужен файл JPEG, PNG или PDF")
    if llm is None:
        raise ServiceUnavailable(
            "Разбор квитанции по фото сейчас недоступен. Попробуйте демо-образцы.",
            "llm_unavailable",
        )
    try:
        parsed = await llm_parsing.extract_receipt(llm, data, content_type)
    except (ValidationError, ValueError) as exc:
        raise BadGateway("Не удалось разобрать квитанцию", "receipt_parse_failed") from exc
    return await _store(session, user_id, llm, parsed)


async def load_sample(
    session: AsyncSession, user_id: uuid.UUID, llm: LLMClient | None, sample_id: str
) -> Receipt:
    """Демо-квитанция; повторная загрузка той же возвращает уже созданную."""
    parsed = samples.load_sample(sample_id)
    existing = await session.scalar(
        select(Receipt).where(Receipt.user_id == user_id, Receipt.sample_id == sample_id)
    )
    return existing or await _store(session, user_id, llm, parsed, sample_id)


async def get_owned(session: AsyncSession, user_id: uuid.UUID, receipt_id: uuid.UUID) -> Receipt:
    receipt = await session.get(Receipt, receipt_id)
    if receipt is None or receipt.user_id != user_id:
        raise NotFound("Квитанция не найдена")
    return receipt


async def list_receipts(session: AsyncSession, user_id: uuid.UUID) -> list[Receipt]:
    stmt = (
        select(Receipt)
        .where(Receipt.user_id == user_id)
        .order_by(Receipt.period.desc().nulls_last(), Receipt.created_at.desc())
    )
    return list((await session.scalars(stmt)).all())


async def patch_line(
    session: AsyncSession,
    user_id: uuid.UUID,
    llm: LLMClient | None,
    receipt_id: uuid.UUID,
    line_id: int,
    patch: LinePatch,
) -> Receipt:
    """Ручная правка строки: пересчитываются итоги, предупреждения и объяснение строки."""
    receipt = await get_owned(session, user_id, receipt_id)
    line = next((x for x in receipt.lines if x.id == line_id), None)
    if line is None:
        raise NotFound("Строка не найдена")
    for field, value in patch.model_dump(exclude_none=True).items():
        setattr(line, field, value)
    line.total = line.accrued + line.recalculation
    receipt.total = sum((x.total for x in receipt.lines), ZERO)
    receipt.warnings = _warnings(
        receipt.period, [line_data(x) for x in receipt.lines], receipt.total
    )
    receipt.status = "needs_review" if receipt.warnings else "parsed"
    receipt.updated_at = utcnow()
    await _explain(llm, receipt, only_line_id=line.id)
    await session.commit()
    return receipt
