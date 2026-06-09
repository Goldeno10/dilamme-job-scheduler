import pytest
from datetime import datetime, timedelta

from app.models.job import Job, Priority
from app.scheduler.base import BaseScheduler
from app.scheduler.heap_scheduler import HeapScheduler


def test_compute_score_priority_order():
    high = Job(type="t", priority=Priority.HIGH, created_at=datetime.utcnow())
    low = Job(type="t", priority=Priority.LOW, created_at=datetime.utcnow())
    assert BaseScheduler.compute_score(high) < BaseScheduler.compute_score(low)


def test_effective_priority_aging():
    job = Job(
        type="t",
        priority=Priority.LOW,
        queued_at=datetime.utcnow() - timedelta(seconds=120),
    )
    assert job.effective_priority() == Priority.HIGH


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
