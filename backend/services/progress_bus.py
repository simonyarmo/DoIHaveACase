"""Redis pub/sub bridge for streaming agent progress events.

`intake_agent` and `lease_parser_agent` run as Celery tasks in a worker
process and publish progress events here; `api/routes/chat.py`'s WebSocket
handler (running in the FastAPI process) subscribes and relays them to the
connected client. Uses the same Redis instance as the Celery broker.
"""

import json
import ssl
from collections.abc import AsyncIterator
from functools import lru_cache

from redis.asyncio import Redis

from config import settings

CHANNEL_PREFIX = "case-progress:"


@lru_cache
def _redis() -> Redis:
    kwargs = {}
    if settings.celery_broker_url.startswith("rediss://"):
        kwargs["ssl_cert_reqs"] = ssl.CERT_REQUIRED
    return Redis.from_url(settings.celery_broker_url, **kwargs)


async def publish(case_id: str, event: dict) -> None:
    await _redis().publish(f"{CHANNEL_PREFIX}{case_id}", json.dumps(event))


async def subscribe(case_id: str) -> AsyncIterator[dict]:
    """Yield progress events for `case_id` as they're published.

    Runs until the caller stops iterating (e.g. on WebSocket disconnect).
    """
    pubsub = _redis().pubsub()
    await pubsub.subscribe(f"{CHANNEL_PREFIX}{case_id}")
    try:
        async for message in pubsub.listen():
            if message["type"] != "message":
                continue
            yield json.loads(message["data"])
    finally:
        await pubsub.unsubscribe(f"{CHANNEL_PREFIX}{case_id}")
        await pubsub.aclose()
