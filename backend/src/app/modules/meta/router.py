from fastapi import APIRouter

from app.core.config import get_settings
from app.core.region import get_region
from app.llm.client import get_llm, vision_available
from app.llm.fallbacks import llm_fallback_total
from app.modules.meta.schemas import FaqItem, Meta

router = APIRouter(tags=["meta"])


@router.get("/meta", response_model=Meta)
async def get_meta() -> Meta:
    """Возможности сервера: фронтенд скрывает то, что без модели не работает."""
    settings = get_settings()
    return Meta(
        llm=get_llm() is not None,
        vision=vision_available(),
        region=settings.region,
        demo_data=settings.demo_data,
        llm_fallbacks=dict(llm_fallback_total),
    )


@router.get("/faq", response_model=list[FaqItem])
async def list_faq() -> list[FaqItem]:
    """Частые вопросы с нормами из справочника региона; работают без модели."""
    return [FaqItem.model_validate(item) for item in get_region().faq]
