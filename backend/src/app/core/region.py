"""Справочники региона (data/regions/<region>/*.yaml): категории, правила, адресаты, тарифы, FAQ."""

from dataclasses import dataclass
from functools import lru_cache
from typing import Any

import yaml

from app.core.config import get_settings


@dataclass(frozen=True)
class Region:
    categories: list[dict[str, Any]]
    rules: dict[str, Any]
    addressees: dict[str, Any]
    tariffs: dict[str, Any]
    classification: dict[str, Any]
    faq: list[dict[str, Any]]

    def category(self, category_id: str) -> dict[str, Any] | None:
        return next((c for c in self.categories if c["id"] == category_id), None)


def _read(name: str) -> Any:
    path = get_settings().region_dir / f"{name}.yaml"
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


@lru_cache
def get_region() -> Region:
    return Region(
        categories=_read("categories"),
        rules=_read("rules"),
        addressees=_read("addressees"),
        tariffs=_read("tariffs"),
        classification=_read("classification"),
        faq=_read("faq"),
    )
