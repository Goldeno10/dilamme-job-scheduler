from datetime import datetime
from enum import IntEnum, StrEnum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field, field_validator


class Priority(IntEnum):
    HIGH = 1
    MEDIUM = 2
    LOW = 3


class JobStatus(StrEnum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class RecurringInterval(StrEnum):
    EVERY_1_MINUTE = "every_1_minute"
    EVERY_5_MINUTES = "every_5_minutes"
    EVERY_1_HOUR = "every_1_hour"


RECURRING_INTERVAL_SECONDS: dict[RecurringInterval, int] = {
    RecurringInterval.EVERY_1_MINUTE: 60,
    RecurringInterval.EVERY_5_MINUTES: 300,
    RecurringInterval.EVERY_1_HOUR: 3600,
}


class JobCreate(BaseModel):
    type: str = Field(..., min_length=1, max_length=100)
    payload: dict[str, Any] = Field(default_factory=dict)
    priority: Priority = Priority.MEDIUM
    scheduled_at: datetime | None = None
    interval: RecurringInterval | None = None
    depends_on: list[str] = Field(default_factory=list)

    @field_validator("depends_on")
    @classmethod
    def validate_depends_on(cls, v: list[str]) -> list[str]:
        return list(dict.fromkeys(v))


class Job(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    type: str
    payload: dict[str, Any] = Field(default_factory=dict)
    priority: Priority = Priority.MEDIUM
    status: JobStatus = JobStatus.PENDING
    retry_count: int = 0
    scheduled_at: datetime | None = None
    interval: RecurringInterval | None = None
    depends_on: list[str] = Field(default_factory=list)
    error: str | None = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    started_at: datetime | None = None
    completed_at: datetime | None = None
    in_dlq: bool = False
    queued_at: datetime | None = None

    def effective_priority(self, now: datetime | None = None) -> int:
        """Starvation prevention: waiting jobs gain priority over time."""
        from app.config import settings

        now = now or datetime.utcnow()
        base = int(self.priority)
        if self.queued_at is None:
            return base
        wait_seconds = (now - self.queued_at).total_seconds()
        boosts = int(wait_seconds // settings.aging_interval_seconds) * settings.aging_boost_levels
        return max(Priority.HIGH, base - boosts)


class JobResponse(Job):
    pass


class DashboardStats(BaseModel):
    pending: int = 0
    processing: int = 0
    completed: int = 0
    failed: int = 0
    cancelled: int = 0
    dlq: int = 0
    total: int = 0


class SSEEvent(BaseModel):
    event: str
    data: dict[str, Any]
