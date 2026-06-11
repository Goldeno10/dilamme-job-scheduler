"""
Benchmark heap vs timing wheel schedulers.
Run: uv run python -m app.api.benchmark
"""

import asyncio
import time
from datetime import timedelta

from fastapi import APIRouter
from pydantic import BaseModel

from app.db.redis_client import close_redis, get_redis
from app.logging_config import setup_logging
from app.models.job import Job, Priority
from app.scheduler.heap_scheduler import HeapScheduler
from app.scheduler.timing_wheel import TimingWheelScheduler
from app.services import job_store
from app.utils.time import utc_now

router = APIRouter()


class BenchmarkResult(BaseModel):
    """
    A model for the results of the benchmark.
    """
    scheduler: str
    jobs: int
    enqueue_ms: float
    dequeue_ms: float
    enqueue_per_job_us: float
    dequeue_per_job_us: float


class BenchmarkResponse(BaseModel):
    results: list[BenchmarkResult]
    tradeoffs: list[str]


async def _benchmark_scheduler(name: str, scheduler, n_jobs: int) -> dict:
    """
    Benchmark the scheduler, meaning that it will enqueue and dequeue the jobs and return the results.
    The jobs are created with a random priority and scheduled at a random time.
    The jobs are enqueued and dequeued in a loop.
    Args:
        name: The name of the scheduler.
        scheduler: The scheduler to benchmark.
        n_jobs: The number of jobs to run the benchmark for.

    Returns:
        A dictionary containing the results of the benchmark.
    """
    redis = await get_redis()
    await redis.flushdb()

    jobs = [
        Job(
            type="send_email",
            payload={"to": f"user{i}@test.com", "subject": "Bench"},
            priority=Priority((i % 3) + 1),
            scheduled_at=utc_now() + timedelta(seconds=i % 10) if i % 5 == 0 else None,
        )
        for i in range(n_jobs)
    ]

    # Persist jobs first (same as create_job in production)
    for job in jobs:
        await job_store.save_job(job)

    # Enqueue benchmark
    start = time.perf_counter()
    for job in jobs:
        await scheduler.enqueue(job)
    enqueue_time = time.perf_counter() - start

    # Dequeue benchmark — wait up to 15s for future-scheduled jobs to become due
    start = time.perf_counter()
    dequeued = 0
    deadline = time.perf_counter() + 15.0
    while dequeued < n_jobs:
        if time.perf_counter() > deadline:
            raise TimeoutError(
                f"Benchmark stuck: dequeued {dequeued}/{n_jobs}. "
                "Scheduled jobs may not have been promoted."
            )
        job = await scheduler.dequeue()
        if job is None:
            await asyncio.sleep(0.05)
            continue
        dequeued += 1
        if hasattr(scheduler, "release_lock"):
            await scheduler.release_lock(job.id)
    dequeue_time = time.perf_counter() - start

    return {
        "scheduler": name,
        "jobs": n_jobs,
        "enqueue_ms": round(enqueue_time * 1000, 2),
        "dequeue_ms": round(dequeue_time * 1000, 2),
        "enqueue_per_job_us": round(enqueue_time / n_jobs * 1e6, 2),
        "dequeue_per_job_us": round(dequeue_time / n_jobs * 1e6, 2),
    }


@router.get("/run", response_model=BenchmarkResponse)
async def api_run_benchmark(n_jobs: int = 500) -> BenchmarkResponse:
    """
    Run the benchmark scheduler for the heap and timing wheel schedulers
    and returns the results in a BenchmarkResponse object.

    Args:
        n_jobs: The number of jobs to run the benchmark for.

    Returns:
        A BenchmarkResponse object containing the results of the benchmark.
    """
    heap_results = await _benchmark_scheduler("heap", HeapScheduler(), n_jobs)
    wheel_results = await _benchmark_scheduler("timing_wheel", TimingWheelScheduler(), n_jobs)
    return BenchmarkResponse(
        results=[BenchmarkResult(**heap_results), BenchmarkResult(**wheel_results)],
        tradeoffs=[
            "Heap: O(log n) per op, global priority ordering, simpler implementation",
            "Timing wheel: O(1) bucket insert, better for time-heavy scheduled workloads",
            "Heap wins on mixed-priority immediate jobs; wheel wins on scheduled bursts",
        ],
    )


async def run_benchmark() -> None:
    """
    Run the benchmark scheduler for the heap and timing wheel schedulers
    and returns the results in a BenchmarkResponse object.

    Args:
        n_jobs: The number of jobs to run the benchmark for.

    Returns:
        A BenchmarkResponse object containing the results of the benchmark.
    """
    setup_logging()
    n = 1000

    heap_results = await _benchmark_scheduler("heap", HeapScheduler(), n)
    wheel_results = await _benchmark_scheduler("timing_wheel", TimingWheelScheduler(), n)

    print("\n=== Scheduler Benchmark Results ===")
    print(f"Jobs tested: {n}\n")
    for r in [heap_results, wheel_results]:
        print(f"  {r['scheduler']}:")
        print(f"    Enqueue total: {r['enqueue_ms']} ms ({r['enqueue_per_job_us']} µs/job)")
        print(f"    Dequeue total: {r['dequeue_ms']} ms ({r['dequeue_per_job_us']} µs/job)")
        print()

    print("Tradeoffs:")
    print("  Heap: O(log n) per op, global priority ordering, simpler")
    print("  Timing wheel: O(1) bucket insert, better for time-heavy workloads")
    print("  Heap wins on mixed-priority immediate jobs; wheel wins on scheduled bursts")

    await close_redis()


if __name__ == "__main__":
    asyncio.run(run_benchmark())
