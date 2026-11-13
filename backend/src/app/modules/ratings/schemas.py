from app.core.schemas import ApiModel


class CompanyRating(ApiModel):
    id: int
    name: str
    score: int | None = None
    issues_total: int
    resolved_share: float | None = None
    on_time_share: float | None = None
    escalated_share: float
    overdue_now: int
    houses_count: int
    districts: list[str]
    top_categories: list[str]


class BreakdownItem(ApiModel):
    key: str
    issues_total: int
    resolved: int


class HouseLoad(ApiModel):
    house_id: int
    address: str
    issues_total: int
    active: int


class CompanyDetail(CompanyRating):
    phones: list[str]
    site: str | None = None
    by_category: list[BreakdownItem]
    by_month: list[BreakdownItem]
    houses: list[HouseLoad]
