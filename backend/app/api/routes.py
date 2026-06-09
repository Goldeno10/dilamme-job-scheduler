import json
from typing import AsyncIterator

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse

from app.models.job import DashboardStats, JobCreate, JobResponse, JobStatus
from app.services import events, job_store
from app.services.job_service import cancel_job, create_job, retry_from_dlq

router = APIRouter()


class WorkflowCreate(BaseModel):
    """
    A model for the creation of a workflow.
    """
    email_to: str
    email_subject: str = "Your Report is Ready"


@router.post("/jobs", response_model=JobResponse, status_code=201)
async def api_create_job(data: JobCreate) -> JobResponse:
    job = await create_job(data)
    return JobResponse(**job.model_dump())


@router.get("/jobs", response_model=list[JobResponse])
async def api_list_jobs(
    status: JobStatus | None = None,
    limit: int = Query(100, le=500),
    offset: int = Query(0, ge=0),
) -> list[JobResponse]:
    jobs = await job_store.list_jobs(status=status, limit=limit, offset=offset)
    return [JobResponse(**j.model_dump()) for j in jobs]


@router.get("/jobs/{job_id}", response_model=JobResponse)
async def api_get_job(job_id: str) -> JobResponse:
    job = await job_store.get_job(job_id)
    if job is None:
        raise HTTPException(404, "Job not found")
    return JobResponse(**job.model_dump())


@router.delete("/jobs/{job_id}", response_model=JobResponse)
async def api_cancel_job(job_id: str) -> JobResponse:
    try:
        job = await cancel_job(job_id)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    return JobResponse(**job.model_dump())


@router.get("/dlq", response_model=list[JobResponse])
async def api_list_dlq(
    limit: int = Query(100, le=500),
    offset: int = Query(0, ge=0),
) -> list[JobResponse]:
    jobs = await job_store.list_dlq_jobs(limit=limit, offset=offset)
    return [JobResponse(**j.model_dump()) for j in jobs]


@router.post("/dlq/{job_id}/retry", response_model=JobResponse)
async def api_retry_dlq(job_id: str) -> JobResponse:
    try:
        job = await retry_from_dlq(job_id)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    return JobResponse(**job.model_dump())


@router.get("/stats", response_model=DashboardStats)
async def api_stats() -> DashboardStats:
    stats = await job_store.get_stats()
    return DashboardStats(**stats)


@router.post("/workflows/report-pipeline", response_model=list[JobResponse])
async def api_create_report_workflow(data: WorkflowCreate) -> list[JobResponse]:
    """
    DAG workflow: Generate Report → Upload File → Send Email
    Each step depends on the previous completing successfully.
    """
    report = await create_job(
        JobCreate(type="generate_report", payload={"report": "monthly"}, priority=1)
    )
    upload = await create_job(
        JobCreate(
            type="upload_file",
            payload={"destination": "s3://reports/"},
            priority=1,
            depends_on=[report.id],
        )
    )
    email = await create_job(
        JobCreate(
            type="send_email",
            payload={"to": data.email_to, "subject": data.email_subject, "body": "Report attached"},
            priority=1,
            depends_on=[upload.id],
        )
    )
    return [
        JobResponse(**report.model_dump()),
        JobResponse(**upload.model_dump()),
        JobResponse(**email.model_dump()),
    ]


async def _sse_generator() -> AsyncIterator[dict]:
    """
    A high-performance Pydantic-validated SSE stream.
    """
    async for event in events.subscribe_events():
        yield {
            "event": event.event,
            "data": json.dumps(event.data, default=str),
        }


@router.get("/events")
async def api_events() -> EventSourceResponse:
    """
    A SSE endpoint for the live events.
    """
    return EventSourceResponse(_sse_generator(), ping=15)
