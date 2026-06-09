# HNG Stage 9 — Background Job Scheduler

Background job scheduler with FastAPI backend, Next.js UI, Redis, independent workers, SSE live updates, heap + timing wheel schedulers, DAG workflows, and DLQ.

## Stack

- **Backend:** FastAPI, Redis, Pydantic, SSE (sse-starlette), structlog, uv
- **Frontend:** Next.js 15, React 19
- **Infra:** Docker, Nginx, GitHub Actions CI

## Quick Start (Docker)

```bash
docker compose up --build
```

- API: http://localhost:8000
- Swagger: http://localhost:8000/docs
- UI: http://localhost:3000

## Local Development

### Prerequisites
- Python 3.11+
- [uv](https://docs.astral.sh/uv/)
- Node.js 20+
- Redis (local image or `docker run -p 6379:6379 redis:7-alpine`)

### Backend

```bash
cd backend
uv sync
cp .env.example .env
uv run uvicorn app.main:app --reload --port 8000
```

### Worker (separate terminal)

```bash
cd backend
uv run python -m app.worker.main
```

### Frontend

```bash
cd frontend
npm install
NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1 npm run dev
```

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/v1/jobs` | Create job |
| GET | `/api/v1/jobs` | List jobs |
| GET | `/api/v1/jobs/{id}` | Get job |
| DELETE | `/api/v1/jobs/{id}` | Cancel job |
| GET | `/api/v1/dlq` | List DLQ jobs |
| POST | `/api/v1/dlq/{id}/retry` | Retry from DLQ |
| GET | `/api/v1/stats` | Dashboard stats |
| GET | `/api/v1/events` | SSE live stream |
| POST | `/api/v1/workflows/report-pipeline` | DAG workflow |
| GET | `/api/v1/benchmark/run` | Scheduler benchmark |

## Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `REDIS_URL` | `redis://localhost:6379/0` | Redis connection |
| `SCHEDULER_ALGORITHM` | `heap` | `heap` or `timing_wheel` |
| `DLQ_ALERT_THRESHOLD` | `5` | DLQ count before alert |
| `AGING_INTERVAL_SECONDS` | `60` | Starvation prevention interval |

## Example Job

```json
{
  "type": "send_email",
  "priority": 1,
  "payload": {
    "to": "test@gmail.com",
    "subject": "Welcome"
  }
}
```

## Documentation

- [Architecture](docs/architecture.md)
- API docs: `/docs` (Swagger)

## Tests

```bash
cd backend
REDIS_URL=redis://localhost:6379/1 uv run pytest -v
```

## Deployment

See `nginx/nginx.conf` for HTTPS reverse proxy. Deploy manually to a VPS with dynamic DNS and Let's Encrypt.

## License

MIT
