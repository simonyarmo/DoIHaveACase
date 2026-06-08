from fastapi import APIRouter
from sqlalchemy import text

from config import settings
from database import async_session_factory

router = APIRouter(tags=["health"])


async def _check_database() -> str:
    try:
        async with async_session_factory() as session:
            await session.execute(text("SELECT 1"))
        return "ok"
    except Exception as exc:  # noqa: BLE001 - surfaced as status string for the health probe
        return f"error: {exc}"


async def _check_redis() -> str:
    if not settings.celery_broker_url:
        return "not_configured"
    try:
        import redis.asyncio as aioredis

        client = aioredis.from_url(settings.celery_broker_url)
        await client.ping()
        await client.aclose()
        return "ok"
    except Exception as exc:  # noqa: BLE001
        return f"error: {exc}"


def _check_azure() -> str:
    missing = [
        name
        for name, value in (
            ("AZURE_FOUNDRY_ENDPOINT", settings.azure_foundry_endpoint),
            ("AZURE_OPENAI_ENDPOINT", settings.azure_openai_endpoint),
            ("AZURE_BLOB_CONNECTION_STRING", settings.azure_blob_connection_string),
        )
        if not value
    ]
    if missing:
        return f"not_configured: missing {', '.join(missing)}"
    return "configured"


@router.get("/health")
async def health_check() -> dict:
    db_status = await _check_database()
    redis_status = await _check_redis()
    azure_status = _check_azure()

    services = {
        "backend": "ok",
        "database": db_status,
        "redis": redis_status,
        "azure": azure_status,
    }
    overall = "ok" if all(v == "ok" or v == "configured" for v in services.values()) else "degraded"

    return {"status": overall, "services": services, "environment": settings.environment}
