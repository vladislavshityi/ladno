"""Анализ квитанций: сравнение месяцев, проверка по тарифам, подсказка для обращения."""

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.region import get_region
from app.llm.client import LLMClient
from app.modules.issues.schemas import RecalculationHint
from app.modules.receipts import diff, explain, overcharge, service, tariffs
from app.modules.receipts.models import CompareExplanation as CompareExplanationRow
from app.modules.receipts.models import Receipt, ReceiptLine
from app.modules.receipts.schemas import Check, Compare, CompareExplanation, Finding

MAINTENANCE = "maintenance"

TITLES = {
    "tariff_mismatch": "Тариф выше справочного",
    "norm_instead_of_meter": "Норматив вместо счётчика",
    "norm_increased": "Норматив с повышающим коэффициентом 1,5",
    "duplicate_line": "Повторяющаяся строка",
    "unexplained_recalculation": "Перерасчёт без пояснения",
}
DESCRIPTIONS = {
    "tariff_mismatch": (
        "Тариф в строке больше тарифа из справочника на этот месяц более чем на 1%. "
        "Возможно, переплата."
    ),
    "norm_instead_of_meter": (
        "В прошлой квитанции начисление шло по счётчику, теперь по нормативу. "
        "Возможно, не учтены показания."
    ),
    "norm_increased": (
        "Начисление по нормативу с повышающим коэффициентом. Возможно, истёк срок поверки счётчика."
    ),
    "duplicate_line": "Строка повторяется с теми же значениями. Возможно, услуга начислена дважды.",
    "unexplained_recalculation": (
        "В строке есть перерасчёт. Возможно, стоит попросить у УК пояснение."
    ),
}


def _compare(base: Receipt, target: Receipt) -> Compare:
    return Compare.model_validate(
        diff.compare(service.receipt_data(base), service.receipt_data(target)),
        from_attributes=True,
    )


async def compare(
    session: AsyncSession, user_id: uuid.UUID, base_id: uuid.UUID, target_id: uuid.UUID
) -> Compare:
    """Расчёт без языковой модели: считается мгновенно."""
    base = await service.get_owned(session, user_id, base_id)
    target = await service.get_owned(session, user_id, target_id)
    return _compare(base, target)


async def compare_explanation(
    session: AsyncSession,
    user_id: uuid.UUID,
    llm: LLMClient | None,
    base_id: uuid.UUID,
    target_id: uuid.UUID,
) -> CompareExplanation:
    """Пояснение берётся из кеша, пока обе квитанции не менялись; иначе пишется заново."""
    base = await service.get_owned(session, user_id, base_id)
    target = await service.get_owned(session, user_id, target_id)
    cached = await session.get(CompareExplanationRow, (base.id, target.id))
    if cached and (cached.base_updated_at, cached.target_updated_at) == (
        base.updated_at,
        target.updated_at,
    ):
        return CompareExplanation(text=cached.text)
    text = await explain.explain_compare(llm, _compare(base, target))
    await session.merge(
        CompareExplanationRow(
            base_id=base.id,
            target_id=target.id,
            base_updated_at=base.updated_at,
            target_updated_at=target.updated_at,
            text=text,
        )
    )
    await session.commit()
    return CompareExplanation(text=text)


async def _previous(session: AsyncSession, user_id: uuid.UUID, receipt: Receipt) -> Receipt | None:
    if not receipt.period:
        return None
    stmt = (
        select(Receipt)
        .where(Receipt.user_id == user_id, Receipt.period < receipt.period)
        .order_by(Receipt.period.desc(), Receipt.created_at.desc())
        .limit(1)
    )
    return await session.scalar(stmt)


def _finding(item: overcharge.FindingData, names: dict[str, str], unverified: set[str]) -> Finding:
    low_trust = item.type == "tariff_mismatch" and item.service_code in unverified
    return Finding(
        type=item.type,
        service_code=item.service_code,
        title=f"{TITLES[item.type]}: {names[item.service_code]}",
        description=DESCRIPTIONS[item.type],
        possible_overpayment=item.possible_overpayment,
        confidence="low" if low_trust else item.confidence,
    )


async def check_receipt(session: AsyncSession, user_id: uuid.UUID, receipt: Receipt) -> Check:
    """Где квитанция может быть завышена. Суммы считает код по тарифам региона."""
    period = receipt.period or ""
    region_tariffs = get_region().tariffs
    previous = await _previous(session, user_id, receipt)
    found = overcharge.find_overcharges(
        service.receipt_data(receipt),
        tariffs.reference_tariffs(region_tariffs, period),
        service.receipt_data(previous) if previous else None,
    )
    names = {x.service_code: x.service_name for x in receipt.lines}
    unverified = tariffs.unverified_services(region_tariffs, period)
    return Check(
        findings=[_finding(x, names, unverified) for x in found],
        total_possible_overpayment=overcharge.total_overpayment(found),
    )


async def recalculation_hint(session: AsyncSession, user_id: uuid.UUID) -> RecalculationHint | None:
    """Строка «содержание жилья» из последней квитанции: по ней просят перерасчёт."""
    stmt = (
        select(ReceiptLine)
        .join(Receipt)
        .where(Receipt.user_id == user_id, ReceiptLine.service_code == MAINTENANCE)
        .order_by(Receipt.period.desc().nulls_last(), Receipt.created_at.desc())
        .limit(1)
    )
    line = await session.scalar(stmt)
    return (
        RecalculationHint(service_name=line.service_name, monthly_amount=line.accrued)
        if line
        else None
    )
