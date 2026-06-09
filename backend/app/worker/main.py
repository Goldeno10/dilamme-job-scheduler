import asyncio
import signal

from app.config import settings
from app.db.redis_client import close_redis, get_redis
from app.logging_config import get_logger, setup_logging
from app.scheduler.factory import get_scheduler
from app.services.job_service import process_job

logger = get_logger(__name__)
_running = True


def _handle_signal(*_):
    global _running
    _running = False


async def worker_loop() -> None:
    setup_logging()
    await get_redis()
    scheduler = get_scheduler()

    logger.info(
        "worker_started",
        algorithm=settings.scheduler_algorithm,
        poll_interval=settings.worker_poll_interval,
    )

    while _running:
        try:
            job = await scheduler.dequeue()
            if job is None:
                await asyncio.sleep(settings.worker_poll_interval)
                continue

            await process_job(job)

            if hasattr(scheduler, "release_lock"):
                await scheduler.release_lock(job.id)

        except Exception as exc:
            logger.error("worker_error", error=str(exc))
            await asyncio.sleep(settings.worker_poll_interval)

    await close_redis()
    logger.info("worker_stopped")


def run() -> None:
    signal.signal(signal.SIGINT, _handle_signal)
    signal.signal(signal.SIGTERM, _handle_signal)
    asyncio.run(worker_loop())


if __name__ == "__main__":
    run()
