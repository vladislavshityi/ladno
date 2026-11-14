from typing import Annotated

from fastapi import APIRouter, Query

from app.core.deps import SessionDep
from app.core.fields import SearchQuery
from app.modules.houses import service
from app.modules.houses.schemas import AddressSuggestion, HouseRead, ManagementCompanyRead

router = APIRouter(tags=["houses"])


@router.get("/addresses/search", response_model=list[AddressSuggestion])
async def search_addresses(
    session: SessionDep, q: Annotated[SearchQuery, Query(min_length=1, max_length=200)]
) -> list[AddressSuggestion]:
    """Поиск дома по адресу: прощает регистр, порядок слов, пропуски и опечатки."""
    return await service.search_addresses(session, q)


@router.get("/houses/{house_id}", response_model=HouseRead)
async def get_house(house_id: int, session: SessionDep) -> HouseRead:
    return HouseRead.model_validate(await service.get_house(session, house_id))


@router.get("/management-companies", response_model=list[ManagementCompanyRead])
async def list_companies(
    session: SessionDep,
    q: Annotated[SearchQuery | None, Query(max_length=200)] = None,
    inn: Annotated[str | None, Query(pattern=r"^\d{10}(\d{2})?$")] = None,
) -> list[ManagementCompanyRead]:
    """Управляющие компании для выбора в профиле; q — часть названия, inn — точный ИНН."""
    companies = await service.list_companies(session, q, inn)
    return [ManagementCompanyRead.model_validate(c) for c in companies]
