from fastapi import APIRouter, HTTPException, status

from api.dependencies import DbDep
from knowledge.ingestion import freshness
from knowledge.ingestion.sources import registry
from schemas.knowledge import IngestResponse, KnowledgeStatusResponse
from tasks.law_refresh import on_demand_ingest

router = APIRouter(prefix="/knowledge", tags=["knowledge"])

_ESTIMATED_INGEST_SECONDS = 300


@router.post("/ingest/{state}", response_model=IngestResponse)
async def ingest_state(state: str, db: DbDep) -> IngestResponse:
    """Trigger on-demand ingestion for a state not yet in Foundry IQ."""
    state = state.upper()
    source = registry.get_state_source(state)
    if source is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"'{state}' is not a supported state",
        )

    await freshness.get_or_create(db, state, source.as_source_urls_dict(), source.review_frequency_days)
    await freshness.record_pipeline_run(db, state, status="ingesting")
    await db.commit()

    on_demand_ingest.delay(state)

    return IngestResponse(status="ingesting", estimated_seconds=_ESTIMATED_INGEST_SECONDS)


@router.get("/status/{state}", response_model=KnowledgeStatusResponse)
async def get_status(state: str, db: DbDep) -> KnowledgeStatusResponse:
    """Poll the ingestion status for a state's knowledge base content."""
    state = state.upper()
    row = await freshness.get_state(db, state)
    if row is None:
        return KnowledgeStatusResponse(state=state, status="not_started", pending_review=False)

    return KnowledgeStatusResponse(
        state=state,
        status=row.last_pipeline_status or "not_started",
        pending_review=row.pending_review,
        last_verified=row.last_verified,
        next_review=row.next_review,
    )
