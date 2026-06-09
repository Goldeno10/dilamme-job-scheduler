"""
Timing wheel scheduler — alternative to heap-based priority queue.

A circular array of slots indexed by time modulo wheel size.
Jobs with future scheduled_at land in the appropriate slot.
Immediate jobs go to the current slot with a priority sub-queue (sorted set per slot).

Tradeoffs vs heap:
- Heap: O(log n) insert/dequeue, global priority ordering, simple
- Timing wheel: O(1) insert for time-bucketed jobs, better for high-volume
  scheduled/recurring workloads; priority within slot still needs ordering
"""

import time
from datetime import datetime

from app.db.redis_client import get_redis
from app.logging_config import get_logger
from app.models.job import Job, JobStatus
from app.scheduler.base import BaseScheduler
from app.scheduler.heap_scheduler import LOCK_PREFIX
from app.services import job_store

logger = get_logger(__name__)

WHEEL_KEY = "wheel:slot:{slot}"
WHEEL_CURSOR = "wheel:cursor"
WHEEL_SCHEDULED = "wheel:scheduled"


class TimingWheelScheduler(BaseScheduler):
    """
    Timing wheel scheduler.

    Args:
        slots: The number of slots in the timing wheel.
        tick_ms: The tick time in milliseconds.

    Returns:
        A TimingWheelScheduler object.
    """
    def __init__(self, slots: int = 3600, tick_ms: int = 1000):
        self.slots = slots
        self.tick_ms = tick_ms

    def _current_slot(self) -> int:
        return int(time.time()) % self.slots

    def _slot_for_time(self, dt: datetime) -> int:
        return int(dt.timestamp()) % self.slots

    def _slot_key(self, slot: int) -> str:
        return WHEEL_KEY.format(slot=slot)

    async def enqueue(self, job: Job) -> None:
        redis = await get_redis()
        now = datetime.utcnow()

        if job.scheduled_at and job.scheduled_at > now:
            target_slot = self._slot_for_time(job.scheduled_at)
            score = job.scheduled_at.timestamp()
            await redis.zadd(WHEEL_SCHEDULED, {job.id: score})
            await redis.zadd(self._slot_key(target_slot), {job.id: self.compute_score(job, now)})
            logger.info("job_scheduled_wheel", job_id=job.id, slot=target_slot)
            return

        if job.depends_on and not await job_store.dependencies_met(job):
            logger.info("job_waiting_dependencies", job_id=job.id)
            return

        job.queued_at = now
        slot = self._current_slot()
        score = self.compute_score(job, now)
        await redis.zadd(self._slot_key(slot), {job.id: score})
        await job_store.save_job(job)
        logger.info("job_enqueued_wheel", job_id=job.id, slot=slot, score=score)

    async def dequeue(self) -> Job | None:
        redis = await get_redis()
        await self.promote_due_scheduled()
        await self._advance_wheel()

        slot = self._current_slot()
        slot_key = self._slot_key(slot)

        while True:
            result = await redis.zpopmin(slot_key, count=1)
            if not result:
                # Check adjacent slots for overdue jobs
                for offset in range(1, min(10, self.slots)):
                    alt_slot = (slot - offset) % self.slots
                    result = await redis.zpopmin(self._slot_key(alt_slot), count=1)
                    if result:
                        break
                if not result:
                    return None

            job_id, _ = result[0]
            job = await job_store.get_job(job_id)
            if job is None or job.status == JobStatus.CANCELLED:
                continue

            if job.depends_on and not await job_store.dependencies_met(job):
                score = self.compute_score(job)
                await redis.zadd(slot_key, {job_id: score})
                continue

            lock_key = f"{LOCK_PREFIX}{job_id}"
            acquired = await redis.set(lock_key, "1", nx=True, ex=30)
            if not acquired:
                score = self.compute_score(job)
                await redis.zadd(slot_key, {job_id: score})
                continue

            return job

    async def _advance_wheel(self) -> None:
        redis = await get_redis()
        await redis.set(WHEEL_CURSOR, self._current_slot())

    async def remove(self, job_id: str) -> None:
        redis = await get_redis()
        pipe = redis.pipeline()
        for i in range(self.slots):
            pipe.zrem(self._slot_key(i), job_id)
        pipe.zrem(WHEEL_SCHEDULED, job_id)
        await pipe.execute()

    async def promote_due_scheduled(self, now: datetime | None = None) -> int:
        redis = await get_redis()
        now = now or datetime.utcnow()
        due = await redis.zrangebyscore(WHEEL_SCHEDULED, "-inf", now.timestamp())
        count = 0
        for job_id in due:
            job = await job_store.get_job(job_id)
            if job is None or job.status == JobStatus.CANCELLED:
                await redis.zrem(WHEEL_SCHEDULED, job_id)
                continue
            await redis.zrem(WHEEL_SCHEDULED, job_id)
            job.scheduled_at = None
            job.queued_at = now
            slot = self._current_slot()
            score = self.compute_score(job, now)
            await redis.zadd(self._slot_key(slot), {job.id: score})
            await job_store.save_job(job)
            count += 1
        return count

    async def size(self) -> int:
        redis = await get_redis()
        total = await redis.zcard(WHEEL_SCHEDULED)
        for i in range(min(self.slots, 100)):  # sample for perf
            total += await redis.zcard(self._slot_key(i))
        return total

    async def release_lock(self, job_id: str) -> None:
        redis = await get_redis()
        await redis.delete(f"{LOCK_PREFIX}{job_id}")
