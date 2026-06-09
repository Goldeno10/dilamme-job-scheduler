from abc import ABC, abstractmethod
from datetime import datetime

from app.models.job import Job


class BaseScheduler(ABC):
    """
    A base class for the schedulers.
    The schedulers are responsible for enqueuing, dequeuing, and
    removing jobs from the queue.
    ABC - Abstract Base Class for the schedulers, used this to
    inherit from and ensure that the schedulers implement the required methods.
    """
    @abstractmethod
    async def enqueue(self, job: Job) -> None:
        ...

    @abstractmethod
    async def dequeue(self) -> Job | None:
        ...

    @abstractmethod
    async def remove(self, job_id: str) -> None:
        ...

    @abstractmethod
    async def promote_due_scheduled(self, now: datetime | None = None) -> int:
        ...

    @abstractmethod
    async def size(self) -> int:
        ...

    @staticmethod
    def compute_score(job: Job, now: datetime | None = None) -> float:
        """
        Heap ordering key (lower = higher priority):
        1. Effective priority (with aging)
        2. Scheduled time
        3. Creation time
        """
        now = now or datetime.utcnow()
        eff_priority = job.effective_priority(now)
        scheduled_ts = job.scheduled_at.timestamp() if job.scheduled_at else 0.0
        created_ts = job.created_at.timestamp()
        # Composite score: priority dominates, then scheduled, then created
        return eff_priority * 1e15 + scheduled_ts * 1e3 + created_ts
