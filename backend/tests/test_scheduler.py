from datetime import datetime, timedelta, timezone

import pytest

from app.models.job import Job, JobCreate, Priority
from app.scheduler.base import BaseScheduler
from app.scheduler.heap_scheduler import HeapScheduler
from app.utils.time import utc_now


def test_compute_score_priority_order():
    high = Job(type="t", priority=Priority.HIGH, created_at=utc_now())
    low = Job(type="t", priority=Priority.LOW, created_at=utc_now())
    assert BaseScheduler.compute_score(high) < BaseScheduler.compute_score(low)


def test_effective_priority_aging():
    job = Job(
        type="t",
        priority=Priority.LOW,
        queued_at=utc_now() - timedelta(seconds=120),
    )
    assert job.effective_priority() == Priority.HIGH


def test_scheduled_at_timezone_aware():
    aware = datetime(2026, 6, 10, 10, 0, 0, tzinfo=timezone.utc)
    job_create = JobCreate(type="send_email", payload={}, scheduled_at=aware)
    assert job_create.scheduled_at is not None
    assert job_create.scheduled_at.tzinfo is not None


@pytest.mark.asyncio
async def test_heap_enqueue_dequeue(redis_url):
    from app.db.redis_client import get_redis

    redis = await get_redis()
    await redis.flushdb()

    scheduler = HeapScheduler()
    job = Job(type="send_email", payload={"to": "a@b.com", "subject": "Hi"}, priority=Priority.HIGH)
    await scheduler.enqueue(job)

    dequeued = await scheduler.dequeue()
    assert dequeued is not None
    assert dequeued.id == job.id
    await scheduler.release_lock(job.id)
