import uuid
from datetime import datetime

from app.core.schemas import ApiModel
from app.modules.issues.models import IssueStatus


class BotIssue(ApiModel):
    id: uuid.UUID
    category_title: str
    status: IssueStatus
    addressee_name: str
    deadline_at: datetime | None = None
    is_overdue: bool = False


class Reminder(ApiModel):
    issue_id: uuid.UUID
    telegram_id: int
    category_title: str
    addressee_name: str
    deadline_at: datetime
    is_overdue: bool
