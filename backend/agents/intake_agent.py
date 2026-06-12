"""Intake research agent.

Orchestrates the background research that runs after a user submits their
intake form (`POST /cases/{case_id}/submit`): verifies the landlord's
business registration, loads the relevant state law, calculates the deposit
return deadline, looks up county court filing procedures, validates the
landlord's service address, and (if a lease was uploaded) parses it.

Each step publishes a progress event over `progress_bus` (consumed by the
`/ws/cases/{case_id}` WebSocket) and records a `conversation_messages` entry,
so the frontend can show a live "research progress" panel and the user has a
permanent record of what the agent found.

A failure in any individual tool call is recorded and surfaced to the user,
but does not abort the rest of the research — the case still reaches the
`assessment` status with whatever findings were gathered.
"""

import asyncio
import logging
import uuid
from collections.abc import Coroutine
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Any

from sqlalchemy import select

from agents import lease_parser_agent
from config import settings
from database import async_session_factory
from knowledge.ingestion import pipeline
from models.agent_session import AgentSession
from models.case import Case
from models.case_detail import CaseDetailsSecurityDeposit
from models.conversation import ConversationMessage
from models.court_tracking import CourtTracking
from models.document import Document
from models.lease_parse import LeaseParseResult
from services import progress_bus
from tasks.celery_app import celery_app
from tools import address_validator, court_lookup, deadline_calculator, foundry_iq, sos_lookup

logger = logging.getLogger(__name__)


@celery_app.task(name="agents.intake_agent.run_intake_research")
def run_intake_research(case_id: str, session_id: str) -> dict:
    return asyncio.run(_run(case_id, session_id))


async def _run(case_id: str, session_id: str) -> dict:
    try:
        return await _run_research(case_id, session_id)
    except Exception as exc:
        logger.exception("Intake research failed for case %s (session %s)", case_id, session_id)
        async with async_session_factory() as db:
            session = await db.get(AgentSession, uuid.UUID(session_id))
            if session is not None:
                session.status = "error"
                session.completed_at = datetime.now(timezone.utc)
                session.error_message = str(exc)[:2000]
            # submit_case set case.status = "researching" before dispatching this
            # run; revert it on failure so the case isn't stuck and can be resubmitted.
            case = await db.get(Case, uuid.UUID(case_id))
            if case is not None and case.status == "researching":
                case.status = "intake"
                case.updated_at = datetime.now(timezone.utc)
            await db.commit()
        await progress_bus.publish(case_id, {"tool": "assessment", "status": "error", "error": str(exc)})
        raise


async def _run_research(case_id: str, session_id: str) -> dict:
    async with async_session_factory() as db:
        case = await db.get(Case, uuid.UUID(case_id))
        if case is None:
            raise ValueError(f"Case {case_id} not found")

        details = (
            await db.execute(
                select(CaseDetailsSecurityDeposit).where(CaseDetailsSecurityDeposit.case_id == uuid.UUID(case_id))
            )
        ).scalar_one_or_none()
        if details is None:
            raise ValueError(f"Case {case_id} has no case_details_security_deposit row")

        session = await db.get(AgentSession, uuid.UUID(session_id))
        state = (case.state or "").upper()
        tools_called: dict[str, Any] = {}

        # 1. SOS lookup — verify landlord entity
        if state and details.landlord_name_as_entered:
            sos_result = await _step(
                case_id, session_id, db, tools_called, "sos_lookup", _sos_summary,
                sos_lookup.lookup_entity(state, details.landlord_name_as_entered),
            )
            if sos_result is not None:
                details.landlord_legal_name = sos_result.get("legal_name") or details.landlord_legal_name
                details.landlord_sos_verified = bool(sos_result.get("verified"))
                details.landlord_sos_status = sos_result.get("status")
                details.landlord_registered_agent = sos_result.get("registered_agent")
                details.landlord_sos_lookup_date = datetime.now(timezone.utc)
                if not details.landlord_address and sos_result.get("address"):
                    details.landlord_address = sos_result["address"]
                await db.flush()

        # 2-4. Load state security-deposit law, ingesting on demand if not yet available
        state_law_chunks: list[dict] = []
        if state:
            state_law_chunks = await _step(
                case_id, session_id, db, tools_called, "state_law",
                lambda chunks: _state_law_summary(state, chunks),
                _load_state_law(db, state),
            ) or []

        # 5. Deadline calculation — pure date logic, can't fail
        deadline_result = deadline_calculator.calculate_deadline(state, details.move_out_date, details.keys_returned_date)
        tools_called["deadline_calculator"] = {"status": "complete", "result": _json_safe(deadline_result)}
        details.deadline_date = deadline_result["deadline_date"]
        details.days_overdue = deadline_result["days_overdue"]
        details.violation_confirmed = deadline_result["violation_confirmed"]
        await db.flush()
        await progress_bus.publish(
            case_id, {"tool": "deadline_calculator", "status": "complete", "result": _json_safe(deadline_result)}
        )
        await _add_message(db, case_id, session_id, _deadline_summary(deadline_result))

        # 6. County court filing procedures
        county = case.county or details.property_county
        court_result = None
        if state:
            court_result = await _step(
                case_id, session_id, db, tools_called, "court_lookup",
                lambda result: _court_summary(result, state, county),
                court_lookup.lookup_court(state, county),
            )
        if court_result and court_result.get("found"):
            await _upsert_court_tracking(db, case_id, court_result)

        # 7. Address validation — verify the landlord's service address
        if details.landlord_address:
            address_result = await _step(
                case_id, session_id, db, tools_called, "address_validator", _address_summary,
                address_validator.validate_address(details.landlord_address),
            )
            if address_result and address_result.get("deliverable") is True and address_result.get("standardized"):
                details.landlord_address = address_result["standardized"]
                await db.flush()

        # 8. Lease parser (if a lease was uploaded and hasn't been parsed yet)
        await db.commit()
        await _maybe_parse_lease(db, case_id, session_id, tools_called)

        # 9. Write findings to the per-case knowledge base
        if state and (sos_result := tools_called.get("sos_lookup", {}).get("result")):
            await foundry_iq.add_document_to_case_kb(
                db, case_id, "landlord-verification", "Landlord Verification", _sos_summary(sos_result), "landlord_verification"
            )
        if state_law_chunks:
            summary_text = "\n\n".join(
                f"{chunk.get('section') or chunk.get('title')}: {chunk.get('content')}" for chunk in state_law_chunks[:3]
            )
            await foundry_iq.add_document_to_case_kb(
                db, case_id, "state-law-summary", f"{state} Security Deposit Law Summary", summary_text, "state_law_summary"
            )

        # 10. Move case to assessment, finalize the agent session
        case.status = "assessment"
        case.updated_at = datetime.now(timezone.utc)
        if session is not None:
            session.status = "completed"
            session.completed_at = datetime.now(timezone.utc)
            session.tools_called = _json_safe(tools_called)
            session.output_summary = _build_output_summary(details, tools_called)

        await _add_message(db, case_id, session_id, "Research complete — your case assessment is ready.", message_type="text")
        await db.commit()

    await progress_bus.publish(case_id, {"tool": "assessment", "status": "complete", "result": {"case_status": "assessment"}})
    return {"case_status": "assessment", "tools_called": _json_safe(tools_called)}


async def _step(
    case_id: str,
    session_id: str,
    db: Any,
    tools_called: dict[str, Any],
    tool_name: str,
    summary_fn: Any,
    coro: Coroutine,
) -> Any:
    """Run one tool call: publish running/complete/error progress events, record
    the result in `tools_called`, and add a conversation message.

    Returns the tool's raw result, or `None` if it raised (the step is
    recorded as an error but does not abort the rest of the research).
    """
    await progress_bus.publish(case_id, {"tool": tool_name, "status": "running"})
    try:
        result = await coro
    except Exception as exc:
        logger.exception("intake_agent step %r failed for case %s", tool_name, case_id)
        tools_called[tool_name] = {"status": "error", "error": str(exc)}
        await progress_bus.publish(case_id, {"tool": tool_name, "status": "error", "error": str(exc)})
        await _add_message(db, case_id, session_id, f"{tool_name.replace('_', ' ').title()} failed: {exc}")
        return None

    tools_called[tool_name] = {"status": "complete", "result": _json_safe(result)}
    await progress_bus.publish(case_id, {"tool": tool_name, "status": "complete", "result": _json_safe(result)})
    await _add_message(db, case_id, session_id, summary_fn(result))
    return result


async def _load_state_law(db: Any, state: str) -> list[dict]:
    query_text = f"{state} security deposit return deadline and notice requirements"
    chunks = await foundry_iq.query_knowledge_base(settings.foundry_kb_state_law, query_text, category=state, top=5)
    if chunks:
        return chunks
    await pipeline.run_on_demand(db, state)
    return await foundry_iq.query_knowledge_base(settings.foundry_kb_state_law, query_text, category=state, top=5)


async def _upsert_court_tracking(db: Any, case_id: str, court_result: dict) -> None:
    row = (await db.execute(select(CourtTracking).where(CourtTracking.case_id == uuid.UUID(case_id)))).scalar_one_or_none()
    if row is None:
        row = CourtTracking(case_id=uuid.UUID(case_id))
        db.add(row)
    row.court_name = court_result.get("court_name")
    row.court_portal_url = court_result.get("filing_url")
    row.last_checked = datetime.now(timezone.utc)
    row.last_status = "found"
    row.entries = {"county": court_result.get("county"), "description": court_result.get("description")}
    await db.flush()


async def _maybe_parse_lease(db: Any, case_id: str, session_id: str, tools_called: dict[str, Any]) -> None:
    lease_doc = (
        await db.execute(
            select(Document)
            .where(Document.case_id == uuid.UUID(case_id), Document.type == "lease")
            .order_by(Document.uploaded_at.desc())
        )
    ).scalars().first()
    if lease_doc is None:
        return

    existing_parse = (
        await db.execute(select(LeaseParseResult).where(LeaseParseResult.document_id == lease_doc.id))
    ).scalar_one_or_none()
    if existing_parse is not None:
        return

    try:
        lease_result = await lease_parser_agent._parse(str(lease_doc.id), case_id)
    except Exception as exc:
        logger.exception("Lease parsing failed during intake research for case %s", case_id)
        tools_called["lease_parser"] = {"status": "error", "error": str(exc)}
        await _add_message(db, case_id, session_id, f"Lease parsing failed: {exc}")
        return

    tools_called["lease_parser"] = {"status": "complete", "result": _json_safe(lease_result)}
    await _add_message(db, case_id, session_id, "Lease parsed — results added to your case file.")


def _sos_summary(result: dict) -> str:
    if result.get("verified"):
        agent = result.get("registered_agent") or "not listed"
        return f"Landlord verified: '{result.get('legal_name')}' (status: {result.get('status')}). Registered agent: {agent}."

    manual = result.get("manual_verification") or {}
    message = f"Landlord could not be verified automatically ({result.get('status')}). {manual.get('why', '')}".strip()
    if manual.get("url"):
        message += f" You can check manually via {manual.get('portal_name')}: {manual['url']}"
    return message


def _state_law_summary(state: str, chunks: list[dict]) -> str:
    if not chunks:
        return f"No {state} security deposit law content is available yet."
    return f"Loaded {state} security deposit law ({len(chunks)} relevant section(s) found)."


def _deadline_summary(result: dict) -> str:
    if result.get("deadline_date") is None:
        return "Could not calculate a deposit return deadline (missing move-out date or unsupported state)."
    standing = "overdue" if result.get("violation_confirmed") else "not yet overdue"
    return f"Deposit return deadline: {result['deadline_date']} ({result['days_overdue']} days, {standing})."


def _court_summary(result: dict, state: str, county: str | None) -> str:
    if not result.get("found"):
        location = county or state
        return f"No court filing procedures are available yet for {location}."
    return f"Court filing info found: {result.get('court_name')} ({result.get('county') or county})."


def _address_summary(result: dict) -> str:
    if result.get("deliverable") is True:
        return f"Landlord address verified and standardized: {result.get('standardized')}."
    if result.get("deliverable") is False:
        return f"Landlord address could not be verified: {result.get('error')}."
    return f"Landlord address validation unavailable: {result.get('error')}."


def _build_output_summary(details: CaseDetailsSecurityDeposit, tools_called: dict[str, Any]) -> str:
    parts = []
    if details.violation_confirmed is not None:
        parts.append("violation confirmed" if details.violation_confirmed else "no violation confirmed")
        if details.days_overdue:
            parts.append(f"{details.days_overdue} days overdue")
    if details.landlord_sos_verified:
        parts.append(f"landlord verified as {details.landlord_legal_name}")
    errors = [name for name, info in tools_called.items() if info.get("status") == "error"]
    if errors:
        parts.append(f"errors: {', '.join(errors)}")
    return "Research complete — " + (", ".join(parts) if parts else "no findings")


async def _add_message(db: Any, case_id: str, session_id: str, content: str, message_type: str = "progress") -> None:
    db.add(
        ConversationMessage(
            case_id=uuid.UUID(case_id),
            session_id=uuid.UUID(session_id),
            role="agent",
            message_type=message_type,
            content=content,
        )
    )
    await db.flush()


def _json_safe(value: Any) -> Any:
    if isinstance(value, dict):
        return {k: _json_safe(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_json_safe(v) for v in value]
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, uuid.UUID):
        return str(value)
    return value
