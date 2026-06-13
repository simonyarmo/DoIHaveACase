"""Celery tasks for the state law ingestion pipeline (phase-02-knowledge.md section 7)."""

import asyncio

from database import celery_session_factory as async_session_factory
from knowledge.ingestion import pipeline
from knowledge.ingestion.freshness import list_due_for_refresh
from services.notifications import send_admin_sms
from tasks.celery_app import celery_app


@celery_app.task(name="tasks.law_refresh.refresh_all_states")
def refresh_all_states() -> list[dict]:
    """Runs every Sunday at 2am.

    Refreshes any state whose `next_review` has passed and is not already
    flagged `pending_review`. States already pending review are not
    auto-published — instead the admin is reminded that a refresh is overdue.
    """
    return asyncio.run(_refresh_all_states())


async def _refresh_all_states() -> list[dict]:
    async with async_session_factory() as db:
        due = await list_due_for_refresh(db)
        to_refresh = [row.state for row in due if not row.pending_review]
        to_remind = [row.state for row in due if row.pending_review]

    results: list[dict] = []
    for state in to_remind:
        send_admin_sms(f"DepositShield: {state} security deposit law refresh is overdue but still pending review.")
        results.append({"state": state, "status": "pending_review_reminder"})

    for state in to_refresh:
        async with async_session_factory() as db:
            results.append(await pipeline.run_refresh(db, state))

    return results


@celery_app.task(name="tasks.law_refresh.on_demand_ingest")
def on_demand_ingest(state: str) -> dict:
    """Triggered by `POST /knowledge/ingest/{state}` for a state not yet in Foundry IQ."""
    return asyncio.run(_on_demand_ingest(state))


async def _on_demand_ingest(state: str) -> dict:
    async with async_session_factory() as db:
        return await pipeline.run_on_demand(db, state)
