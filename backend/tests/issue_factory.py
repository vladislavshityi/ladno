import uuid
from datetime import timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import utcnow
from app.modules.houses.models import House
from app.modules.issues.models import Issue, IssueStatus
from app.modules.users.models import User


def make_issue(user: User, house: House, status: IssueStatus, **fields) -> Issue:
    """Обращение к УК дома, поданное 40 дней назад со сроком ответа 10 дней."""
    submitted = utcnow() - timedelta(days=40)
    values = dict(
        id=uuid.uuid4(),
        user_id=user.id,
        category="elevator",
        house_id=house.id,
        addressee_key="managing_company",
        route={},
        status=status,
        submitted_at=submitted,
        deadline_at=submitted + timedelta(days=10),
    )
    return Issue(**(values | fields))


async def add(session: AsyncSession, *issues: Issue) -> None:
    session.add_all(issues)
    await session.flush()
