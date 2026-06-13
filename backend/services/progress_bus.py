"""Redis pub/sub bridge for streaming agent progress events.

`intake_agent` and `lease_parser_agent` run as Celery tasks in a worker
process and publish progress events here; `api/routes/chat.py`'s WebSocket
handler (running in the FastAPI process) subscribes and relays them to the
connected client. Uses the same Redis instance as the Celery broker.
"""

import json
import ssl
from collections.abc import AsyncIterator

from redis.asyncio import Redis

from config import settings

CHANNEL_PREFIX = "case-progress:"


def _new_redis() -> Redis:
    # A fresh client per call rather than a cached singleton: a cached
    # client's connections are bound to the event loop active when it was
    # first used, which breaks ("Event loop is closed") once Celery's
    # `asyncio.run()` moves on to a new loop for the next task.
    kwargs = {}
    if settings.celery_broker_url.startswith("rediss://"):
        kwargs["ssl_cert_reqs"] = ssl.CERT_REQUIRED
    return Redis.from_url(settings.celery_broker_url, **kwargs)


async def publish(case_id: str, event: dict) -> None:
    redis = _new_redis()
    try:
        await redis.publish(f"{CHANNEL_PREFIX}{case_id}", json.dumps(event))
    finally:
        await redis.aclose()


async def subscribe(case_id: str) -> AsyncIterator[dict]:
    """Yield progress events for `case_id` as they're published.

    Runs until the caller stops iterating (e.g. on WebSocket disconnect).
    """
    redis = _new_redis()
    try:
        pubsub = redis.pubsub()
        try:
            await pubsub.subscribe(f"{CHANNEL_PREFIX}{case_id}")
            async for message in pubsub.listen():
                if message["type"] != "message":
                    continue
                yield json.loads(message["data"])
        finally:
            await pubsub.unsubscribe(f"{CHANNEL_PREFIX}{case_id}")
            await pubsub.aclose()
    finally:
        await redis.aclose()
