"""Тарифы региона: что действовало в данном месяце. Чистые функции над данными tariffs.yaml."""

import re
from datetime import date
from decimal import Decimal
from typing import Any

PERIOD_RE = re.compile(r"^\d{4}-(0[1-9]|1[0-2])$")


def _active(tariffs: dict[str, Any], period: str) -> list[tuple[dict, dict]]:
    """Пары (услуга, период действия) на месяц, у которых есть значение и документ."""
    if not PERIOD_RE.match(period):
        return []
    day = date(int(period[:4]), int(period[5:7]), 1)
    found = []
    for entry in tariffs.get("tariffs", []):
        for p in entry["periods"]:
            in_range = date.fromisoformat(p["from"]) <= day <= date.fromisoformat(p["to"])
            if in_range and p["value"] is not None and p.get("document"):
                found.append((entry, p))
    return found


def reference_tariffs(tariffs: dict[str, Any], period: str) -> dict[str, list[Decimal]]:
    """Допустимые тарифы на месяц по service_code, в единицах строки квитанции."""
    result: dict[str, list[Decimal]] = {}
    for entry, p in _active(tariffs, period):
        factor = Decimal(entry.get("volume_factor", "1"))
        result.setdefault(entry["service_code"], []).append(Decimal(p["value"]) * factor)
    return result


def service_options(tariffs: dict[str, Any], period: str) -> list[dict[str, Any]]:
    """Услуги для ручного ввода; tariff подставляется, только если на месяц он один однозначный."""
    reference = reference_tariffs(tariffs, period)
    options = []
    for item in tariffs.get("services", []):
        values = reference.get(item["code"], [])
        options.append(
            {
                "service_code": item["code"],
                "name": item["name"],
                "unit": item["unit"],
                "tariff": values[0] if len(values) == 1 else None,
            }
        )
    return options


def unverified_services(tariffs: dict[str, Any], period: str) -> set[str]:
    """Услуги, тариф которых не подтверждён первоисточником: выводы по ним менее уверенные."""
    return {entry["service_code"] for entry, p in _active(tariffs, period) if not p["verified"]}


def service_note(tariffs: dict[str, Any], service_code: str) -> str:
    return " ".join(tariffs.get("service_notes", {}).get(service_code, "").split())


def finding_basis(tariffs: dict[str, Any], finding_type: str) -> list[dict[str, Any]]:
    """Нормы для заявления на перерасчёт: text, source, verified."""
    return tariffs.get("finding_basis", {}).get(finding_type, [])


def tariff_document(
    tariffs: dict[str, Any], period: str, service_code: str
) -> dict[str, Any] | None:
    """Постановление об утверждении тарифа на месяц в виде нормы: text, source, verified."""
    for entry, p in _active(tariffs, period):
        if entry["service_code"] == service_code:
            text = "Тариф утверждён постановлением"
            return {"text": text, "source": p["document"], "verified": p["verified"]}
    return None
