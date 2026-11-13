"""Заявление в УК на перерасчёт по находкам проверки. Суммы берутся только из расчёта кода."""

import uuid
from datetime import date
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import Conflict
from app.core.region import get_region
from app.core.templates import render
from app.modules.receipts import analysis, overcharge, service, tariffs
from app.modules.receipts.models import Receipt
from app.modules.receipts.schemas import Finding, RecalculationLetter
from app.modules.users.applicant import applicant_line
from app.modules.users.models import User

DEFAULT_ADDRESSEE = "Управляющая организация"


def _basis(findings: list[Finding], period: str) -> list[dict[str, Any]]:
    region_tariffs = get_region().tariffs
    items: list[dict[str, Any]] = []
    for f in findings:
        items += tariffs.finding_basis(region_tariffs, f.type)
        document = tariffs.tariff_document(region_tariffs, period, f.service_code)
        if f.type == "tariff_mismatch" and document:
            items.append(document)
    unique = {(i["text"], i["source"]): i for i in items}
    return list(unique.values())


def _context(receipt: Receipt, findings: list[Finding], applicant: str) -> dict[str, Any]:
    total = sum((f.possible_overpayment for f in findings), overcharge.ZERO)
    return {
        "applicant": applicant,
        "addressee_name": receipt.uk_name or DEFAULT_ADDRESSEE,
        "period": receipt.period,
        "account_last4": receipt.account_last4,
        "findings": findings,
        "total": format(total, "f"),
        "basis": _basis(findings, receipt.period or ""),
        "date": date.today().strftime("%d.%m.%Y"),
    }


async def build_letter(
    session: AsyncSession, user: User, receipt_id: uuid.UUID, finding_types: list[str]
) -> RecalculationLetter:
    receipt = await service.get_owned(session, user.id, receipt_id)
    found = (await analysis.check_receipt(session, user.id, receipt)).findings
    chosen = [f for f in found if not finding_types or f.type in finding_types]
    if not chosen:
        raise Conflict(
            "В квитанции не найдено нарушений, по которым можно просить перерасчёт", "no_findings"
        )
    return RecalculationLetter(
        text=render("letters/recalculation.j2", **_context(receipt, chosen, applicant_line(user)))
    )
