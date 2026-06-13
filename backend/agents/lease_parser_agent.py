"""Lease parsing agent.

Extracts structured lease terms (parties, dates, deposit amount, notice
requirements, pet policy, etc.) from an uploaded lease document via the LLM,
cross-checks the notice requirements against the case's state-law knowledge
base, and writes the results to `lease_parse_results`.

Runs as a Celery task (`parse_lease`), but the async `_parse` implementation
is also called directly by `intake_agent` when a lease was uploaded during
intake — so the work isn't dispatched twice.
"""

import asyncio
import io
import json
import logging
import re
import uuid
from datetime import date

import pdfplumber
from docx import Document as DocxDocument
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.sql import func

from config import settings
from database import celery_session_factory as async_session_factory
from models.case import Case
from models.case_detail import CaseDetailsSecurityDeposit
from models.document import Document
from models.lease_parse import LeaseParseResult
from services import blob_storage, llm_client, progress_bus
from tasks.celery_app import celery_app
from tools import foundry_iq

logger = logging.getLogger(__name__)

_MAX_LEASE_CHARS = 60_000
_JSON_FENCE_RE = re.compile(r"^```(?:json)?\s*|\s*```$", re.MULTILINE)

_EXTRACTION_FIELDS = (
    "tenant_legal_name",
    "landlord_legal_name",
    "property_address",
    "lease_start_date",
    "lease_end_date",
    "deposit_amount",
    "notice_required_days",
    "notice_method",
    "pet_policy",
    "early_termination_clause",
    "maintenance_responsibilities",
    "notice_compliant",
)


@celery_app.task(name="agents.lease_parser_agent.parse_lease")
def parse_lease(document_id: str, case_id: str) -> dict:
    return asyncio.run(_parse(document_id, case_id))


async def _parse(document_id: str, case_id: str) -> dict:
    await progress_bus.publish(case_id, {"tool": "lease_parser", "status": "running"})

    try:
        parsed = await _parse_and_store(document_id, case_id)
    except Exception as exc:
        logger.exception("Lease parsing failed for document %s (case %s)", document_id, case_id)
        await progress_bus.publish(case_id, {"tool": "lease_parser", "status": "error", "error": str(exc)})
        raise

    await progress_bus.publish(case_id, {"tool": "lease_parser", "status": "complete", "result": parsed})
    return parsed


async def _parse_and_store(document_id: str, case_id: str) -> dict:
    async with async_session_factory() as db:
        document = await db.get(Document, uuid.UUID(document_id))
        if document is None or document.storage_path is None:
            raise ValueError(f"Document {document_id} not found or has no storage path")

        case = await db.get(Case, uuid.UUID(case_id))
        state = (case.state or "").upper() if case and case.state else ""

        data = blob_storage.download_bytes(settings.azure_blob_container_documents, document.storage_path)
        if data is None:
            raise ValueError(f"Document {document_id} blob not found at {document.storage_path}")

        text = _extract_text(data, document.file_type, document.file_name)

        state_law_context: list[dict] = []
        if state:
            state_law_context = await foundry_iq.query_knowledge_base(
                settings.foundry_kb_state_law,
                "security deposit notice requirements early termination pet policy waivers",
                category=state,
                top=5,
            )

        messages = _build_messages(text, state, state_law_context)
        raw_response = await llm_client.chat_completion(messages, temperature=0.1)
        parsed = _parse_extraction_response(raw_response)

        notice_required_days = _safe_int(parsed.get("notice_required_days"))
        result_values = {
            "tenant_legal_name": parsed.get("tenant_legal_name"),
            "landlord_legal_name": parsed.get("landlord_legal_name"),
            "property_address": parsed.get("property_address"),
            "lease_start_date": _safe_date(parsed.get("lease_start_date")),
            "lease_end_date": _safe_date(parsed.get("lease_end_date")),
            "deposit_amount": _safe_float(parsed.get("deposit_amount")),
            "notice_required_days": notice_required_days,
            "notice_method": parsed.get("notice_method"),
            "pet_policy": parsed.get("pet_policy"),
            "early_termination_clause": parsed.get("early_termination_clause"),
            "maintenance_responsibilities": parsed.get("maintenance_responsibilities"),
            "notice_compliant": _safe_bool(parsed.get("notice_compliant")),
            "flagged_clauses": parsed.get("flagged_clauses") if isinstance(parsed.get("flagged_clauses"), list) else [],
            "raw_parse_output": parsed,
            "confidence_score": _safe_float(parsed.get("confidence_score")),
        }

        # Upsert on document_id: the upload-time Celery dispatch and the
        # intake agent's direct call can both parse the same document, so a
        # plain insert would violate `uq_lease_parse_results_document_id`.
        stmt = pg_insert(LeaseParseResult).values(
            document_id=document.id, case_id=uuid.UUID(case_id), **result_values
        )
        stmt = stmt.on_conflict_do_update(index_elements=["document_id"], set_={**result_values, "parsed_at": func.now()})
        await db.execute(stmt)

        details = (
            await db.execute(
                select(CaseDetailsSecurityDeposit).where(CaseDetailsSecurityDeposit.case_id == uuid.UUID(case_id))
            )
        ).scalar_one_or_none()
        if details is not None and notice_required_days is not None:
            details.lease_required_notice_days = notice_required_days

        document.status = "processed"

        await foundry_iq.add_document_to_case_kb(
            db, case_id, f"lease-parse-{document_id}", "Lease Parse Summary", _build_summary(parsed), "lease_parse"
        )

        await db.commit()

    return parsed


def _extract_text(data: bytes, file_type: str | None, file_name: str | None) -> str:
    """Extract plain text from a lease document based on its file type."""
    file_type = (file_type or "").lower()
    file_name = (file_name or "").lower()

    if "pdf" in file_type or file_name.endswith(".pdf"):
        with pdfplumber.open(io.BytesIO(data)) as pdf:
            return "\n".join(page.extract_text() or "" for page in pdf.pages)

    if "word" in file_type or "officedocument" in file_type or file_name.endswith(".docx"):
        doc = DocxDocument(io.BytesIO(data))
        return "\n".join(paragraph.text for paragraph in doc.paragraphs)

    return data.decode("utf-8", errors="ignore")


def _build_messages(lease_text: str, state: str, state_law_context: list[dict]) -> list[dict]:
    if state_law_context:
        context_text = "\n\n".join(
            f"### {chunk.get('section') or chunk.get('title') or ''}\n{chunk.get('content') or ''}"
            for chunk in state_law_context
        )
    else:
        context_text = "No state-law context available."

    system = (
        "You are a legal-document extraction assistant analyzing a residential lease for a "
        f"security-deposit dispute{f' in {state}' if state else ''}. Extract the fields below "
        "as a single strict JSON object — no markdown, no commentary, just JSON. Use null for "
        "anything not stated in the lease.\n\n"
        "Fields:\n"
        "- tenant_legal_name (string or null)\n"
        "- landlord_legal_name (string or null)\n"
        "- property_address (string or null)\n"
        "- lease_start_date (ISO 8601 YYYY-MM-DD or null)\n"
        "- lease_end_date (ISO 8601 YYYY-MM-DD or null)\n"
        "- deposit_amount (number or null)\n"
        "- notice_required_days (integer days of notice the lease requires for move-out / "
        "lease termination, or null)\n"
        "- notice_method (string describing how notice must be delivered, or null)\n"
        "- pet_policy (string summary, or null)\n"
        "- early_termination_clause (string summary or verbatim text, or null)\n"
        "- maintenance_responsibilities (string summary of tenant vs landlord responsibilities, or null)\n"
        "- notice_compliant (true, false, or null — whether the lease's notice terms are "
        "consistent with the state law excerpts below; null if the excerpts don't address this)\n"
        "- flagged_clauses (array of {\"clause\": string, \"concern\": string} for lease clauses "
        "that may conflict with or be unenforceable under the state law excerpts below, e.g. "
        "waiving statutory rights or non-refundable deposit language where the state requires "
        "deposits be refundable. Empty array if none.)\n"
        "- confidence_score (number from 0 to 1 reflecting overall extraction confidence)\n\n"
        f"--- {state or 'State'} security deposit law excerpts ---\n{context_text}"
    )
    return [
        {"role": "system", "content": system},
        {"role": "user", "content": f"--- Lease text ---\n{lease_text[:_MAX_LEASE_CHARS]}"},
    ]


def _parse_extraction_response(raw_response: str) -> dict:
    cleaned = _JSON_FENCE_RE.sub("", raw_response.strip())
    try:
        parsed = json.loads(cleaned)
    except json.JSONDecodeError:
        logger.exception("Lease parser LLM response was not valid JSON")
        return {"_parse_error": "LLM response was not valid JSON", "_raw_response": raw_response[:5000]}
    return parsed if isinstance(parsed, dict) else {"_parse_error": "LLM response was not a JSON object"}


def _build_summary(parsed: dict) -> str:
    lines = ["Lease parse results:"]
    for key in _EXTRACTION_FIELDS:
        value = parsed.get(key)
        if value is not None:
            lines.append(f"- {key}: {value}")

    flagged = parsed.get("flagged_clauses")
    if isinstance(flagged, list) and flagged:
        lines.append("- flagged_clauses:")
        for item in flagged:
            if isinstance(item, dict):
                lines.append(f"  - {item.get('clause')}: {item.get('concern')}")

    return "\n".join(lines)


def _safe_date(value: object) -> date | None:
    if not isinstance(value, str):
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


def _safe_float(value: object) -> float | None:
    if value is None:
        return None
    try:
        return float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None


def _safe_int(value: object) -> int | None:
    if value is None:
        return None
    try:
        return int(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None


def _safe_bool(value: object) -> bool | None:
    if isinstance(value, bool):
        return value
    if isinstance(value, str) and value.strip().lower() in ("true", "false"):
        return value.strip().lower() == "true"
    return None
