from typing import Annotated

from fastapi import APIRouter, Query

from app.core.deps import SessionDep
from app.modules.ratings import service
from app.modules.ratings.schemas import CompanyDetail, CompanyRating

router = APIRouter(prefix="/ratings", tags=["ratings"])


@router.get("/companies", response_model=list[CompanyRating])
async def list_company_ratings(
    session: SessionDep,
    district: str | None = None,
    sort: Annotated[service.SortKey, Query()] = "score",
) -> list[CompanyRating]:
    """Рейтинг УК по обращениям жителей. Только агрегаты, вход не нужен."""
    return await service.list_ratings(session, district, sort)


@router.get("/companies/{company_id}", response_model=CompanyDetail)
async def get_company_rating(company_id: int, session: SessionDep) -> CompanyDetail:
    """Метрики УК, разбивка по категориям и месяцам, дома с активными обращениями."""
    return await service.company_detail(session, company_id)
