import uuid
from datetime import datetime

from pydantic import BaseModel

from app.modules.issues.models import IssueStatus


class BotIssue(BaseModel):
    id: uuid.UUID
    category_title: str
    status: IssueStatus
    addressee_name: str
    deadline_at: datetime | None = None
    is_overdue: bool = False


class Reminder(BaseModel):
    issue_id: uuid.UUID
    telegram_id: int
    category_title: str
    addressee_name: str
    deadline_at: datetime
    is_overdue: bool
