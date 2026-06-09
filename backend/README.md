# Job Scheduler Backend

FastAPI + Redis background job scheduler.

```bash
uv sync
uv run uvicorn app.main:app --reload
uv run python -m app.worker.main
```
