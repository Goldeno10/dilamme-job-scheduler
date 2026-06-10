from typing import Any, AsyncIterator

from redis.exceptions import TimeoutError as RedisTimeoutError

from app.db.redis_client import get_redis, get_redis_pubsub
from app.models.job import SSEEvent

EVENTS_CHANNEL = "job:events"


async def publish_event(event: str, data: dict[str, Any]) -> None:
    redis = await get_redis()
    payload = SSEEvent(event=event, data=data).model_dump_json()
    await redis.publish(EVENTS_CHANNEL, payload)


async def subscribe_events() -> AsyncIterator[SSEEvent]:
    redis = await get_redis_pubsub()
    pubsub = redis.pubsub()
    await pubsub.subscribe(EVENTS_CHANNEL)
    try:
        async for message in pubsub.listen():
            if message["type"] != "message":
                continue
            raw = message["data"]
            if isinstance(raw, bytes):
                raw = raw.decode()
            yield SSEEvent.model_validate_json(raw)
    except RedisTimeoutError:
        # Should not occur with socket_timeout=None; swallow if it does
        return
    finally:
        await pubsub.unsubscribe(EVENTS_CHANNEL)
        await pubsub.aclose()
