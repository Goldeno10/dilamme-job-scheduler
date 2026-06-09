from app.config import settings
from app.scheduler.base import BaseScheduler
from app.scheduler.heap_scheduler import HeapScheduler
from app.scheduler.timing_wheel import TimingWheelScheduler


def get_scheduler() -> BaseScheduler:
    """
    Get the scheduler based on the scheduler algorithm.
    Args:
        settings: The settings object.

    Returns:
        A scheduler object.
    """
    if settings.scheduler_algorithm == "timing_wheel":
        return TimingWheelScheduler(
            slots=settings.timing_wheel_slots,
            tick_ms=settings.timing_wheel_tick_ms,
        )
    return HeapScheduler()
