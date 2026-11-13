from typing import Annotated

from fastapi import APIRouter, Query

from app.core.deps import SessionDep
from app.modules.map import service
from app.modules.map.schemas import MapPoint

router = APIRouter(prefix="/map", tags=["map"])


@router.get("/points", response_model=list[MapPoint])
async def list_map_points(
    session: SessionDep,
    category: str | None = None,
    days: Annotated[int, Query(ge=1, le=365)] = 90,
    active: bool = False,
) -> list[MapPoint]:
    """Дома с обращениями за период: число, категории, УК с баллом. Вход не нужен."""
    return await service.list_points(session, category, days, active)
