"""Tracks the age and review status of each state's law file in `law_freshness`."""

from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.law_freshness import LawFreshness


async def get_or_create(
    db: AsyncSession,
    state: str,
    source_urls: dict,
    review_frequency_days: int,
) -> LawFreshness:
    """Return the `law_freshness` row for `state`, creating it if needed.

    The source registry is the source of truth for `source_urls` and
    `review_frequency_days`, so an existing row (e.g. one of the TX/CA/FL
    rows pre-seeded by migration 014) is kept in sync with the registry.
    """
    result = await db.execute(select(LawFreshness).where(LawFreshness.state == state))
    row = result.scalar_one_or_none()
    if row is not None:
        row.source_urls = source_urls
        row.review_frequency_days = review_frequency_days
        await db.flush()
        return row

    row = LawFreshness(
        state=state,
        source_urls=source_urls,
        review_frequency_days=review_frequency_days,
    )
    db.add(row)
    await db.flush()
    return row


async def record_pipeline_run(
    db: AsyncSession,
    state: str,
    *,
    status: str,
    foundry_source_id: str | None = None,
    pending_review: bool = False,
    changes: dict | None = None,
) -> LawFreshness:
    """Record the outcome of a pipeline run for `state`.

    On a successful, non-flagged `ready` run, also bumps `last_verified` to
    now and schedules `next_review` based on `review_frequency_days`.
    """
    result = await db.execute(select(LawFreshness).where(LawFreshness.state == state))
    row = result.scalar_one_or_none()
    if row is None:
        raise ValueError(f"No law_freshness row for state {state!r} — call get_or_create first")

    now = datetime.now(timezone.utc)
    row.last_pipeline_run = now
    row.last_pipeline_status = status
    row.last_pipeline_changes = changes
    row.pending_review = pending_review

    if foundry_source_id is not None:
        row.foundry_source_id = foundry_source_id

    if status == "ready" and not pending_review:
        row.last_verified = now

    # Every terminal status (i.e. not the in-flight "ingesting" status) schedules
    # its own next attempt on the normal cadence — otherwise stub/invalid/error
    # states never get a `next_review` and `list_due_for_refresh` re-attempts a
    # full pipeline run for them every week indefinitely.
    if status != "ingesting":
        row.next_review = now + timedelta(days=row.review_frequency_days)

    await db.flush()
    return row


async def list_due_for_refresh(db: AsyncSession) -> list[LawFreshness]:
    """Return all states whose `next_review` has passed (or was never set)."""
    now = datetime.now(timezone.utc)
    result = await db.execute(
        select(LawFreshness).where((LawFreshness.next_review.is_(None)) | (LawFreshness.next_review <= now))
    )
    return list(result.scalars().all())


async def get_state(db: AsyncSession, state: str) -> LawFreshness | None:
    result = await db.execute(select(LawFreshness).where(LawFreshness.state == state.upper()))
    return result.scalar_one_or_none()
