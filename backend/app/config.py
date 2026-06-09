from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    redis_url: str = "redis://localhost:6379/0"
    app_name: str = "Job Scheduler"
    debug: bool = False

    # Retry backoff base seconds: attempt 1→~1s, 2→~5s, 3→~25s
    retry_backoff_base: float = 1.0
    max_retries: int = 3

    # Starvation prevention: boost effective priority every N seconds waiting
    aging_interval_seconds: int = 60
    aging_boost_levels: int = 1

    # DLQ alert threshold
    dlq_alert_threshold: int = 5
    dlq_alert_email: str = "ops@dilamme.com"

    # Scheduler algorithm: "heap" or "timing_wheel"
    scheduler_algorithm: str = "heap"

    # Worker poll interval
    worker_poll_interval: float = 0.5
    worker_lock_ttl: int = 30

    # Timing wheel
    timing_wheel_slots: int = 3600
    timing_wheel_tick_ms: int = 1000


settings = Settings()
