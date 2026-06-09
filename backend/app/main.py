from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.benchmark import router as benchmark_router
from app.api.routes import router
from app.config import settings
from app.db.redis_client import close_redis, get_redis
from app.logging_config import setup_logging


@asynccontextmanager
async def lifespan(_app: FastAPI):
    setup_logging()
    await get_redis()
    yield
    await close_redis()


app = FastAPI(
    title=settings.app_name,
    description="HNG Stage 9 Background Job Scheduler API",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router, prefix="/api/v1", tags=["jobs"])
app.include_router(benchmark_router, prefix="/api/v1/benchmark", tags=["benchmark"])


@app.get("/health")
async def health():
    return {"status": "ok", "scheduler": settings.scheduler_algorithm}
