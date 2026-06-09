"""
Heap-based priority queue using Redis sorted set.

The sorted set acts as a min-heap: members are job IDs, scores are composite
priority keys. ZPOPMIN atomically removes the highest-priority job.

Ordering (ascending score = dequeued first):
  1. Effective priority (1=high, boosted by aging)
  2. scheduled_at timestamp
  3. created_at timestamp
"""

from datetime import datetime

from app.db.redis_client import get_redis
from app.logging_config import get_logger
from app.models.job import Job, JobStatus
from app.scheduler.base import BaseScheduler
from app.services import job_store

logger = get_logger(__name__)

HEAP_QUEUE = "queue:heap"
SCHEDULED_SET = "queue:scheduled"
LOCK_PREFIX = "lock:job:"


class HeapScheduler(BaseScheduler):
    async def enqueue(self, job: Job) -> None:
        redis = await get_redis()
        now = datetime.utcnow()

        if job.scheduled_at and job.scheduled_at > now:
            await redis.zadd(SCHEDULED_SET, {job.id: job.scheduled_at.timestamp()})
            logger.info("job_scheduled", job_id=job.id, scheduled_at=job.scheduled_at.isoformat())
            return

        if job.depends_on:
            if not await job_store.dependencies_met(job):
                logger.info("job_waiting_dependencies", job_id=job.id, depends_on=job.depends_on)
                return

        job.queued_at = now
        score = self.compute_score(job, now)
        await redis.zadd(HEAP_QUEUE, {job.id: score})
        await job_store.save_job(job)
        logger.info("job_enqueued_heap", job_id=job.id, score=score, priority=job.priority)

    async def dequeue(self) -> Job | None:
        redis = await get_redis()
        await self.promote_due_scheduled()

        while True:
            result = await redis.zpopmin(HEAP_QUEUE, count=1)
            if not result:
                return None

            job_id, _score = result[0]
            job = await job_store.get_job(job_id)
            if job is None:
                continue

            if job.status == JobStatus.CANCELLED:
                logger.info("job_skipped_cancelled", job_id=job_id)
                continue

            if job.depends_on and not await job_store.dependencies_met(job):
                # Re-enqueue with updated score (may have aged)
                job.queued_at = datetime.utcnow()
                score = self.compute_score(job)
                await redis.zadd(HEAP_QUEUE, {job_id: score})
                continue

            # Acquire distributed lock for duplicate protection
            lock_key = f"{LOCK_PREFIX}{job_id}"
            acquired = await redis.set(lock_key, "1", nx=True, ex=30)
            if not acquired:
                # Another worker has it; re-enqueue
                score = self.compute_score(job)
                await redis.zadd(HEAP_QUEUE, {job_id: score})
                continue

            return job

    async def remove(self, job_id: str) -> None:
        redis = await get_redis()
        pipe = redis.pipeline()
        pipe.zrem(HEAP_QUEUE, job_id)
        pipe.zrem(SCHEDULED_SET, job_id)
        await pipe.execute()

    async def promote_due_scheduled(self, now: datetime | None = None) -> int:
        redis = await get_redis()
        now = now or datetime.utcnow()
        due = await redis.zrangebyscore(SCHEDULED_SET, "-inf", now.timestamp())
        count = 0
        for job_id in due:
            job = await job_store.get_job(job_id)
            if job is None or job.status == JobStatus.CANCELLED:
                await redis.zrem(SCHEDULED_SET, job_id)
                continue
            await redis.zrem(SCHEDULED_SET, job_id)
            job.scheduled_at = None
            job.queued_at = now
            score = self.compute_score(job, now)
            await redis.zadd(HEAP_QUEUE, {job.id: score})
            await job_store.save_job(job)
            count += 1
            logger.info("job_promoted_from_schedule", job_id=job_id)
        return count

    async def size(self) -> int:
        redis = await get_redis()
        heap_size = await redis.zcard(HEAP_QUEUE)
        scheduled_size = await redis.zcard(SCHEDULED_SET)
        return heap_size + scheduled_size

    async def release_lock(self, job_id: str) -> None:
        redis = await get_redis()
        await redis.delete(f"{LOCK_PREFIX}{job_id}")
