import random
from datetime import datetime, timedelta

from app.config import settings
from app.handlers import HANDLERS
from app.logging_config import get_logger
from app.models.job import (
    RECURRING_INTERVAL_SECONDS,
    Job,
    JobCreate,
    JobStatus,
    RecurringInterval,
)
from app.scheduler.factory import get_scheduler
from app.services import events, job_store

logger = get_logger(__name__)


async def create_job(data: JobCreate) -> Job:
    job = Job(
        type=data.type,
        payload=data.payload,
        priority=data.priority,
        scheduled_at=data.scheduled_at,
        interval=data.interval,
        depends_on=data.depends_on,
    )

    await job_store.save_job(job)
    if data.depends_on:
        await job_store.register_dependents(job.id, data.depends_on)

    scheduler = get_scheduler()
    await scheduler.enqueue(job)

    await events.publish_event("job_created", job.model_dump(mode="json"))
    logger.info(
        "job_created",
        job_id=job.id,
        type=job.type,
        priority=job.priority,
        depends_on=job.depends_on,
    )
    return job


async def cancel_job(job_id: str) -> Job:
    job = await job_store.get_job(job_id)
    if job is None:
        raise ValueError(f"Job {job_id} not found")

    if job.status in (JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED):
        raise ValueError(f"Cannot cancel job in status {job.status}")

    previous_status = job.status
    job.status = JobStatus.CANCELLED
    job.updated_at = datetime.utcnow()
    await job_store.save_job(job)

    scheduler = get_scheduler()
    await scheduler.remove(job_id)

    await events.publish_event("job_cancelled", job.model_dump(mode="json"))
    logger.info(
        "job_cancelled",
        job_id=job_id,
        previous_status=previous_status,
        note="If already processing, worker checks status before completion",
    )
    return job


async def retry_from_dlq(job_id: str) -> Job:
    job = await job_store.get_job(job_id)
    if job is None or not job.in_dlq:
        raise ValueError(f"Job {job_id} not in DLQ")

    job.status = JobStatus.PENDING
    job.retry_count = 0
    job.error = None
    job.in_dlq = False
    job.queued_at = None
    job.updated_at = datetime.utcnow()
    await job_store.save_job(job)

    scheduler = get_scheduler()
    await scheduler.enqueue(job)

    await events.publish_event("job_retried_from_dlq", job.model_dump(mode="json"))
    logger.info("job_retried_from_dlq", job_id=job_id)
    return job


def _backoff_seconds(attempt: int) -> float:
    """Exponential backoff with jitter: ~1s, ~5s, ~25s."""
    base = settings.retry_backoff_base * (5 ** (attempt - 1))
    jitter = random.uniform(0.5, 1.5)
    return base * jitter


async def _schedule_retry(job: Job, error: str) -> None:
    job.retry_count += 1
    job.error = error
    job.status = JobStatus.PENDING
    job.updated_at = datetime.utcnow()

    delay = _backoff_seconds(job.retry_count)
    job.scheduled_at = datetime.utcnow() + timedelta(seconds=delay)
    await job_store.save_job(job)

    scheduler = get_scheduler()
    await scheduler.enqueue(job)

    await events.publish_event("job_retry", job.model_dump(mode="json"))
    logger.info(
        "retry_attempted",
        job_id=job.id,
        attempt=job.retry_count,
        delay_seconds=round(delay, 2),
        error=error,
    )


async def _move_to_dlq(job: Job, error: str) -> None:
    job.status = JobStatus.FAILED
    job.error = error
    job.in_dlq = True
    job.completed_at = datetime.utcnow()
    job.updated_at = datetime.utcnow()
    await job_store.save_job(job)

    await events.publish_event("job_failed", job.model_dump(mode="json"))
    logger.info("job_failed", job_id=job.id, error=error, in_dlq=True)

    # Check DLQ threshold alert
    stats = await job_store.get_stats()
    if stats["dlq"] >= settings.dlq_alert_threshold:
        await _send_dlq_alert(stats["dlq"])


async def _send_dlq_alert(dlq_count: int) -> None:
    """Simulated alert email when DLQ crosses threshold."""
    logger.warning(
        "dlq_threshold_alert",
        dlq_count=dlq_count,
        threshold=settings.dlq_alert_threshold,
        alert_email=settings.dlq_alert_email,
        message=f"DLQ has {dlq_count} jobs (threshold: {settings.dlq_alert_threshold})",
    )
    await events.publish_event(
        "dlq_alert",
        {
            "dlq_count": dlq_count,
            "threshold": settings.dlq_alert_threshold,
            "email": settings.dlq_alert_email,
        },
    )


async def _schedule_recurring(job: Job) -> None:
    if not job.interval:
        return
    seconds = RECURRING_INTERVAL_SECONDS[RecurringInterval(job.interval)]
    new_job = Job(
        type=job.type,
        payload=job.payload,
        priority=job.priority,
        interval=job.interval,
        depends_on=job.depends_on,
        scheduled_at=datetime.utcnow() + timedelta(seconds=seconds),
    )
    await job_store.save_job(new_job)
    scheduler = get_scheduler()
    await scheduler.enqueue(new_job)
    logger.info("recurring_job_scheduled", parent_id=job.id, new_job_id=new_job.id, interval=job.interval)
    await events.publish_event("job_created", new_job.model_dump(mode="json"))


async def _unlock_dependents(job: Job) -> None:
    dependents = await job_store.get_dependents(job.id)
    scheduler = get_scheduler()
    for dep_id in dependents:
        dep_job = await job_store.get_job(dep_id)
        if dep_job and dep_job.status == JobStatus.PENDING:
            if await job_store.dependencies_met(dep_job):
                await scheduler.enqueue(dep_job)
                logger.info("dependent_job_enqueued", job_id=dep_id, completed_parent=job.id)


async def process_job(job: Job) -> None:
    """Process a single job — called by worker."""
    handler = HANDLERS.get(job.type)
    if handler is None:
        await _move_to_dlq(job, f"No handler for job type: {job.type}")
        return

    job.status = JobStatus.PROCESSING
    job.started_at = datetime.utcnow()
    job.updated_at = datetime.utcnow()
    await job_store.save_job(job)
    await events.publish_event("job_started", job.model_dump(mode="json"))
    logger.info("job_started", job_id=job.id, type=job.type)

    try:
        result = await handler(job.payload)

        # Check cancellation mid-processing
        fresh = await job_store.get_job(job.id)
        if fresh and fresh.status == JobStatus.CANCELLED:
            logger.info(
                "job_cancelled_during_processing",
                job_id=job.id,
                note="Handler completed but result discarded; job remains cancelled",
            )
            return

        job.status = JobStatus.COMPLETED
        job.completed_at = datetime.utcnow()
        job.updated_at = datetime.utcnow()
        job.payload["_result"] = result
        await job_store.save_job(job)

        await events.publish_event("job_completed", job.model_dump(mode="json"))
        logger.info("job_completed", job_id=job.id, type=job.type)

        await _unlock_dependents(job)
        await _schedule_recurring(job)

    except Exception as exc:
        error_msg = str(exc)
        if job.retry_count < settings.max_retries:
            await _schedule_retry(job, error_msg)
        else:
            await _move_to_dlq(job, error_msg)
