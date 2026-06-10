import redis.asyncio as aioredis
from redis.asyncio import Redis

from app.config import settings

_redis: Redis | None = None
_redis_pubsub: Redis | None = None


async def get_redis() -> Redis:
    global _redis
    if _redis is None:
        _redis = aioredis.from_url(settings.redis_url, decode_responses=True)
    return _redis


async def get_redis_pubsub() -> Redis:
    """Dedicated client for pub/sub — no socket read timeout (SSE long-poll)."""
    global _redis_pubsub
    if _redis_pubsub is None:
        _redis_pubsub = aioredis.from_url(
            settings.redis_url,
            decode_responses=True,
            socket_timeout=None,
            socket_connect_timeout=10,
        )
    return _redis_pubsub


async def close_redis() -> None:
    global _redis, _redis_pubsub
    if _redis is not None:
        await _redis.aclose()
        _redis = None
    if _redis_pubsub is not None:
        await _redis_pubsub.aclose()
        _redis_pubsub = None
