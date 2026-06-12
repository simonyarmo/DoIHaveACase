import ssl

from celery import Celery
from celery.schedules import crontab

from config import settings

celery_app = Celery(
    "depositshield",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=["tasks.test_tasks", "tasks.law_refresh", "agents.intake_agent", "agents.lease_parser_agent"],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    broker_connection_retry_on_startup=True,
    beat_schedule={
        "refresh-state-law-weekly": {
            "task": "tasks.law_refresh.refresh_all_states",
            "schedule": crontab(hour=2, minute=0, day_of_week=0),
        },
    },
)

# Upstash (and other managed Redis providers) require TLS — `rediss://` URLs
# need an explicit ssl_cert_reqs or both the broker and result backend raise
# ValueError on first use.
if settings.celery_broker_url.startswith("rediss://"):
    celery_app.conf.broker_use_ssl = {"ssl_cert_reqs": ssl.CERT_REQUIRED}
if settings.celery_result_backend.startswith("rediss://"):
    celery_app.conf.redis_backend_use_ssl = {"ssl_cert_reqs": ssl.CERT_REQUIRED}
