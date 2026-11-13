"""Балл управляющей компании по её обращениям. Чистые функции без IO."""

from dataclasses import dataclass

MIN_ISSUES = 3
RESOLVED_WEIGHT = 0.5
ON_TIME_WEIGHT = 0.3
NOT_ESCALATED_WEIGHT = 0.2


@dataclass(frozen=True)
class CompanyStats:
    issues_total: int
    resolved: int
    rejected: int
    no_response: int
    overdue_now: int  # поданные, но не закрытые обращения с истёкшим сроком ответа
    on_time: int  # ответ получен до срока
    escalated: int

    @property
    def decided(self) -> int:
        """Обращения с известным исходом: решены, отказ, нет ответа или срок уже истёк."""
        return self.resolved + self.rejected + self.no_response + self.overdue_now

    @property
    def resolved_share(self) -> float | None:
        return self.resolved / self.decided if self.decided else None

    @property
    def on_time_share(self) -> float | None:
        return self.on_time / self.decided if self.decided else None

    @property
    def escalated_share(self) -> float:
        return self.escalated / self.issues_total if self.issues_total else 0.0


def compute_score(stats: CompanyStats) -> int | None:
    """0–100; None, если данных мало: меньше MIN_ISSUES обращений или ни одного исхода."""
    resolved_share, on_time_share = stats.resolved_share, stats.on_time_share
    if stats.issues_total < MIN_ISSUES or resolved_share is None or on_time_share is None:
        return None
    return round(
        100
        * (
            RESOLVED_WEIGHT * resolved_share
            + ON_TIME_WEIGHT * on_time_share
            + NOT_ESCALATED_WEIGHT * (1 - stats.escalated_share)
        )
    )
