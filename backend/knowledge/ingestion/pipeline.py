"""Ingestion pipeline orchestrator — seed, refresh, and on-demand modes
(phase-02-knowledge.md section 3).
"""

import logging
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession

from knowledge.ingestion import fetcher, freshness, parser, uploader, validator
from knowledge.ingestion.sources import registry
from services.notifications import send_admin_sms

logger = logging.getLogger(__name__)

STATE_LAW_DIR = Path(__file__).resolve().parent.parent / "state_law"


def _read_local_markdown(state: str) -> str:
    return (STATE_LAW_DIR / f"{state.upper()}.md").read_text(encoding="utf-8")


def _is_stub(markdown: str) -> bool:
    return validator.extract_header(markdown).get("Status") == "stub"


async def run_seed(db: AsyncSession, state: str) -> dict:
    """Seed mode: register `law_freshness` for `state`, and — if its local
    markdown file is fully populated — upload and index it in
    `kb-state-law-security-deposit`. Stub files are registered but left for
    a later on-demand ingest.
    """
    state = state.upper()
    source = registry.get_state_source(state)
    if source is None:
        raise ValueError(f"No source registry entry for state {state!r}")

    await freshness.get_or_create(db, state, source.as_source_urls_dict(), source.review_frequency_days)
    uploader.upload_court_procedures(state, source.court_procedures)

    markdown = _read_local_markdown(state)
    if _is_stub(markdown):
        await freshness.record_pipeline_run(db, state, status="stub")
        await db.commit()
        return {"state": state, "status": "stub"}

    result = validator.validate_markdown(markdown)
    if not result.is_valid:
        await freshness.record_pipeline_run(
            db, state, status="invalid", changes={"missing_sections": result.missing_sections}
        )
        await db.commit()
        return {"state": state, "status": "invalid", "missing_sections": result.missing_sections}

    header = validator.extract_header(markdown)
    foundry_source_id = uploader.upload_state_law(state, markdown, source.statute_url, header["Last Verified"])
    await freshness.record_pipeline_run(db, state, status="ready", foundry_source_id=foundry_source_id)
    await db.commit()
    return {"state": state, "status": "ready", "foundry_source_id": foundry_source_id}


async def run_refresh(db: AsyncSession, state: str) -> dict:
    """Refresh / on-demand mode: fetch the live source, parse it with the LLM,
    validate against the currently-published version, and either publish or
    flag for human review.
    """
    state = state.upper()
    source = registry.get_state_source(state)
    if source is None:
        raise ValueError(f"No source registry entry for state {state!r}")

    await freshness.get_or_create(db, state, source.as_source_urls_dict(), source.review_frequency_days)
    await freshness.record_pipeline_run(db, state, status="ingesting")
    await db.commit()

    existing_markdown = uploader.get_existing_state_law(state)
    reference_markdown = existing_markdown or _read_local_markdown("TX")

    raw = await fetcher.fetch_source(source.statute_url)
    new_markdown = await parser.parse_state_law(state, source.statute_url, raw, reference_markdown=reference_markdown)

    result = validator.validate_markdown(new_markdown, existing_markdown=existing_markdown)

    if not result.is_valid:
        await freshness.record_pipeline_run(
            db, state, status="invalid", changes={"missing_sections": result.missing_sections}
        )
        await db.commit()
        return {"state": state, "status": "invalid", "missing_sections": result.missing_sections}

    if result.needs_review:
        uploader.upload_pending_review(state, new_markdown)
        await freshness.record_pipeline_run(
            db,
            state,
            status="pending_review",
            pending_review=True,
            changes={"changed_critical_sections": result.changed_critical_sections},
        )
        await db.commit()
        send_admin_sms(
            f"DepositShield: {state} security deposit law has changes pending review "
            f"in sections: {', '.join(result.changed_critical_sections)}."
        )
        return {
            "state": state,
            "status": "pending_review",
            "changed_critical_sections": result.changed_critical_sections,
        }

    header = validator.extract_header(new_markdown)
    foundry_source_id = uploader.upload_state_law(state, new_markdown, source.statute_url, header["Last Verified"])
    (STATE_LAW_DIR / f"{state}.md").write_text(new_markdown, encoding="utf-8")
    await freshness.record_pipeline_run(db, state, status="ready", foundry_source_id=foundry_source_id)
    await db.commit()
    return {"state": state, "status": "ready", "foundry_source_id": foundry_source_id}


async def run_on_demand(db: AsyncSession, state: str) -> dict:
    """On-demand mode: a user selected a state not yet in Foundry IQ — runs the
    same pipeline as refresh, populating the state's file for the first time.
    """
    return await run_refresh(db, state)
