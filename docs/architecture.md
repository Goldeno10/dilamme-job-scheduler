# Architecture — Background Job Scheduler

## Overview

A distributed background job scheduler built for Dilamme (HNG Stage 9). Jobs are created via REST API, queued in Redis-backed schedulers, processed by independent workers, and tracked in real time via SSE.

```
┌─────────────┐     REST/SSE      ┌──────────────┐
│  Next.js UI │ ◄──────────────► │   FastAPI    │
└─────────────┘                   └──────┬───────┘
                                         │
                    ┌────────────────────┼────────────────────┐
                    │                    │                    │
               ┌────▼────┐        ┌──────▼──────┐      ┌─────▼─────┐
               │  Redis  │◄──────►│   Worker 1  │      │ Worker 2  │
               │ (store, │        └─────────────┘      └───────────┘
               │  queue, │
               │ pubsub) │
               └─────────┘
```

## Components

### API (FastAPI)
- Job CRUD, cancellation, DLQ retry
- DAG workflow endpoint (`POST /workflows/report-pipeline`)
- SSE live events (`GET /events`)
- Swagger docs at `/docs`

### Workers
- Independent processes (`python -m app.worker.main`)
- Poll scheduler for jobs, acquire distributed locks, execute handlers
- Do not block the API

### Redis
| Key | Purpose |
|-----|---------|
| `job:{id}` | Job JSON document |
| `jobs:index` | All job IDs |
| `queue:heap` | Min-heap sorted set (score = priority key) |
| `queue:scheduled` | Future scheduled jobs |
| `dlq:index` | Dead-letter job IDs |
| `lock:job:{id}` | Duplicate protection (SET NX, 30s TTL) |
| `job:events` | Pub/sub channel for SSE |

## Job Lifecycle

```
pending → processing → completed
                    ↘ failed (after 3 retries → DLQ)
         ↘ cancelled
```

### Cancellation During Processing
If a job is cancelled while a worker is processing it, the worker checks status after the handler returns. If cancelled, the result is discarded and status remains `cancelled`. This avoids race conditions without complex rollback.

## Heap Scheduler

Redis sorted set acts as a **min-heap**. Score computed as:

```
score = effective_priority × 10¹⁵ + scheduled_ts × 10³ + created_ts
```

Dequeue: `ZPOPMIN` — O(log n).

### Starvation Prevention (Aging)
- **Threshold:** 60 seconds waiting in queue
- **Boost:** Effective priority improves by 1 level per 60s (3→2→1)
- A low-priority job waiting 2+ minutes competes as high priority

## Timing Wheel (Alternative)

Circular slot array indexed by `timestamp % slots`. Jobs bucketed by time slot; priority ordering within slot via sorted set.

### Benchmark (1000 jobs, local Redis)

| Scheduler | Enqueue | Dequeue |
|-----------|---------|---------|
| Heap | ~120ms | ~180ms |
| Timing Wheel | ~95ms | ~150ms |

**Tradeoffs:**
- **Heap:** Global priority ordering, simpler, O(log n)
- **Timing Wheel:** O(1) time-bucket insert, better for scheduled bursts; priority across buckets is coarser

Run: `GET /api/v1/benchmark/run` or `uv run python -m app.api.benchmark`

## Retries & DLQ

| Attempt | Backoff (with jitter) |
|---------|----------------------|
| 1 | ~1s |
| 2 | ~5s |
| 3 | ~25s |

After 3 failures → DLQ. Manual retry resets count.

### DLQ Alert
- **Threshold:** 5 jobs in DLQ
- **Action:** Structured log + SSE `dlq_alert` event (simulated email to `ops@dilamme.com`)

## DAG Workflows

Jobs have `depends_on: [job_id, ...]`. A job enters the queue only when all dependencies are `completed`. On completion, dependents are enqueued.

Built-in workflow: **Generate Report → Upload File → Send Email**

## Duplicate Protection

`SET lock:job:{id} NX EX 30` before processing. If lock fails, job is re-queued. Lock released after processing.

## Logging

Structured JSON via `structlog`:
- `job_created`, `job_started`, `job_completed`, `job_failed`, `job_cancelled`, `retry_attempted`, `dlq_threshold_alert`

## Deployment

- **Local:** `docker-compose.yml` at repo root (builds from source)
- **Production:** `deploy/docker-compose.yml` pulls images from GHCR
- **HTTPS:** Dockerized Nginx + Certbot via `deploy/init-letsencrypt.sh`

See `docs/deployment.md` and `deploy/README.md`.
