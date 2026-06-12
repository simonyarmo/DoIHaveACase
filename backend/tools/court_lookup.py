"""County small-claims court / filing-procedure lookup.

Queries the `kb-court-procedures` Foundry IQ knowledge base (populated by
`knowledge/ingestion/uploader.upload_court_procedures` from
`state_sources.yaml`'s `court_procedures` entries).
"""

from config import settings
from tools import foundry_iq


async def lookup_court(state: str, county: str | None) -> dict:
    """Return filing-procedure info for `county` (or the best match for `state`
    if `county` isn't given or has no registered entry).

    Returns `{"found": False, "state": ..., "county": ...}` if `state` has no
    registered court-procedure sources yet (e.g. CA, FL today) — the case can
    still proceed without this information.
    """
    state = state.upper()
    query_text = f"{county} small claims filing procedures" if county else "small claims filing procedures"

    results = await foundry_iq.query_knowledge_base(settings.foundry_kb_court_procedures, query_text, category=state, top=5)
    if not results:
        return {"found": False, "state": state, "county": county}

    match = None
    if county:
        match = next((r for r in results if (r.get("section") or "").lower() == county.lower()), None)
    match = match or results[0]

    return {
        "found": True,
        "court_name": match.get("title"),
        "county": match.get("section"),
        "filing_url": match.get("source_url"),
        "description": match.get("content"),
    }
