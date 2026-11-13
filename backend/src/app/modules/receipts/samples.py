"""Демо-квитанции из data/samples/receipts: готовый разбор без загрузки файла."""

import json
from pathlib import Path

from app.core.config import get_settings
from app.core.errors import NotFound
from app.modules.receipts.schemas import ParsedReceipt, ReceiptSample


def _paths() -> list[Path]:
    return sorted((get_settings().data_dir / "samples" / "receipts").glob("*.json"))


def list_samples() -> list[ReceiptSample]:
    return [
        ReceiptSample(id=p.stem, title=json.loads(p.read_text(encoding="utf-8"))["title"])
        for p in _paths()
    ]


def load_sample(sample_id: str) -> ParsedReceipt:
    path = next((p for p in _paths() if p.stem == sample_id), None)
    if path is None:
        raise NotFound("Демо-квитанция не найдена")
    return ParsedReceipt.model_validate_json(path.read_text(encoding="utf-8"))
