from datetime import datetime

from app.db.redis_client import get_redis
from app.models.job import Job, JobStatus

JOBS_INDEX = "jobs:index"
JOB_KEY = "job:{id}"
DLQ_INDEX = "dlq:index"
DEPENDENTS_KEY = "job:dependents:{id}"


def _job_key(job_id: str) -> str:
    return JOB_KEY.format(id=job_id)


async def save_job(job: Job) -> Job:
    redis = await get_redis()
    job.updated_at = datetime.utcnow()
    pipe = redis.pipeline()
    pipe.set(_job_key(job.id), job.model_dump_json())
    pipe.sadd(JOBS_INDEX, job.id)
    if job.in_dlq:
        pipe.sadd(DLQ_INDEX, job.id)
    else:
        pipe.srem(DLQ_INDEX, job.id)
    await pipe.execute()
    return job


async def get_job(job_id: str) -> Job | None:
    redis = await get_redis()
    data = await redis.get(_job_key(job_id))
    if not data:
        return None
    return Job.model_validate_json(data)


async def list_jobs(status: JobStatus | None = None, limit: int = 100, offset: int = 0) -> list[Job]:
    redis = await get_redis()
    ids = await redis.smembers(JOBS_INDEX)
    jobs: list[Job] = []
    for job_id in ids:
        job = await get_job(job_id)
        if job is None:
            continue
        if status is not None and job.status != status:
            continue
        jobs.append(job)
    jobs.sort(key=lambda j: j.created_at, reverse=True)
    return jobs[offset : offset + limit]


async def list_dlq_jobs(limit: int = 100, offset: int = 0) -> list[Job]:
    redis = await get_redis()
    ids = list(await redis.smembers(DLQ_INDEX))
    jobs: list[Job] = []
    for job_id in ids:
        job = await get_job(job_id)
        if job and job.in_dlq:
            jobs.append(job)
    jobs.sort(key=lambda j: j.updated_at, reverse=True)
    return jobs[offset : offset + limit]


async def get_stats() -> dict[str, int]:
    redis = await get_redis()
    ids = await redis.smembers(JOBS_INDEX)
    stats = {
        "pending": 0,
        "processing": 0,
        "completed": 0,
        "failed": 0,
        "cancelled": 0,
        "dlq": 0,
        "total": 0,
    }
    for job_id in ids:
        job = await get_job(job_id)
        if job is None:
            continue
        stats["total"] += 1
        stats[job.status.value] = stats.get(job.status.value, 0) + 1
        if job.in_dlq:
            stats["dlq"] += 1
    return stats


async def register_dependents(job_id: str, depends_on: list[str]) -> None:
    redis = await get_redis()
    pipe = redis.pipeline()
    for dep_id in depends_on:
        pipe.sadd(DEPENDENTS_KEY.format(id=dep_id), job_id)
    await pipe.execute()


async def get_dependents(job_id: str) -> list[str]:
    redis = await get_redis()
    return list(await redis.smembers(DEPENDENTS_KEY.format(id=job_id)))


async def dependencies_met(job: Job) -> bool:
    for dep_id in job.depends_on:
        dep = await get_job(dep_id)
        if dep is None or dep.status != JobStatus.COMPLETED:
            return False
    return True
