"""Jinja2-шаблоны текстов: письма, шаги подачи, пояснения к квитанциям."""

from functools import lru_cache

from jinja2 import Environment, FileSystemLoader, StrictUndefined

from app.core.config import get_settings


@lru_cache
def _env() -> Environment:
    return Environment(
        loader=FileSystemLoader(get_settings().templates_dir),
        autoescape=False,  # письма — обычный текст
        undefined=StrictUndefined,
        trim_blocks=True,
        lstrip_blocks=True,
    )


def render(name: str, **context: object) -> str:
    return _env().get_template(name).render(**context).strip()
