from app.core.schemas import ApiModel


class MapCompany(ApiModel):
    id: int
    name: str
    score: int | None = None


class MapPoint(ApiModel):
    house_id: int
    lat: float
    lon: float
    address: str
    total: int
    active: int
    emergency: bool
    categories: dict[str, int]
    management_company: MapCompany | None = None
