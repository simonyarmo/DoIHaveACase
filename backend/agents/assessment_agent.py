"""Case assessment agent — the deterministic "law application engine".

Runs once intake research completes (triggered in-process by
`agents.intake_agent._run_research`) and can be re-run manually via
`POST /cases/{case_id}/assessment/refresh`. Evaluates the collected case
details against `tools.assessment_rules.STATE_ASSESSMENT_RULES`, writes the
result onto `case_details_security_deposit`, generates an action-plan
timeline for cases worth pursuing, and moves `case.status` to
`"action_plan"` or `"closed_no_case"`.

This agent never calls an LLM — every finding traces back to a rule in
`tools.assessment_rules` (and, ultimately, to a cited section of the
relevant `knowledge/state_law/<STATE>.md` file).
"""

import asyncio
import logging
import uuid
from datetime import date, datetime, timedelta, timezone
from typing import Any

from sqlalchemy import delete, select

from database import celery_session_factory as async_session_factory
from models.case import Case
from models.case_detail import CaseDetailsSecurityDeposit
from models.conversation import ConversationMessage
from models.lease_parse import LeaseParseResult
from models.timeline import TimelineEvent
from services import progress_bus
from tasks.celery_app import celery_app
from tools import foundry_iq
from tools.assessment_rules import STATE_ASSESSMENT_RULES, evaluate_assessment

logger = logging.getLogger(__name__)


@celery_app.task(name="agents.assessment_agent.run_assessment")
def run_assessment(case_id: str) -> dict:
    return asyncio.run(_run(case_id))


async def _run(case_id: str) -> dict:
    try:
        return await _run_assessment(case_id)
    except Exception as exc:
        logger.exception("Assessment failed for case %s", case_id)
        await progress_bus.publish(case_id, {"tool": "assessment", "status": "error", "error": str(exc)})
        raise


async def _run_assessment(case_id: str) -> dict:
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

        lease = (
            await db.execute(
                select(LeaseParseResult)
                .where(LeaseParseResult.case_id == uuid.UUID(case_id))
                .order_by(LeaseParseResult.parsed_at.desc())
            )
        ).scalars().first()

        state = (case.state or "").upper()
        rules = STATE_ASSESSMENT_RULES.get(state)

        result = evaluate_assessment(details, lease, rules, state)

        details.violation_confirmed = result["violation_confirmed"]
        details.bad_faith_indicators = result["bad_faith_indicators"]
        details.case_strength = result["case_strength"]
        details.findings_good = result["findings_good"]
        details.findings_caution = result["findings_caution"]
        details.findings_bad = result["findings_bad"]
        details.defenses_likely = result["defenses_likely"]
        details.estimated_recovery_min = result["estimated_recovery_min"]
        details.estimated_recovery_max = result["estimated_recovery_max"]
        details.penalty_multiplier = result["penalty_multiplier"]
        details.exceeds_jurisdiction = result["exceeds_jurisdiction"]
        details.jurisdiction_options = result["jurisdiction_options"]
        details.recommended_path = result["recommended_path"]
        details.notice_compliant = result["notice_compliant"]
        details.notice_risk_amount = result["notice_risk_amount"]
        await db.flush()

        case.status = "closed_no_case" if result["case_strength"] == "no_case" else "action_plan"
        case.updated_at = datetime.now(timezone.utc)

        await _generate_action_plan(db, case_id, details, rules)

        summary = _build_summary(result)
        db.add(ConversationMessage(case_id=uuid.UUID(case_id), role="agent", message_type="text", content=summary))
        await foundry_iq.add_document_to_case_kb(db, case_id, "assessment-summary", "Case Assessment Summary", summary, "assessment_summary")

        await db.commit()

    publish_result = {
        "case_status": case.status,
        "case_strength": result["case_strength"],
        "estimated_recovery_min": result["estimated_recovery_min"],
        "estimated_recovery_max": result["estimated_recovery_max"],
    }
    await progress_bus.publish(case_id, {"tool": "assessment", "status": "complete", "result": publish_result})
    return publish_result


async def _generate_action_plan(db: Any, case_id: str, details: CaseDetailsSecurityDeposit, rules: dict | None) -> None:
    """Replace any existing agent-generated timeline with a fresh 5-step plan.

    Only cases worth pursuing (`strong`/`moderate`) get a plan — `weak` cases
    aren't ripe yet and `no_case` cases have nothing to act on. Re-running
    this clears any previously generated plan first, so `/refresh` doesn't
    duplicate events or leave a stale plan behind if the case strength
    changed.
    """
    await db.execute(delete(TimelineEvent).where(TimelineEvent.case_id == uuid.UUID(case_id), TimelineEvent.source == "agent"))

    if details.case_strength not in ("strong", "moderate"):
        await db.flush()
        return

    demand_wait_days = (rules or {}).get("demand_letter_wait_days", 14)
    court_name = "Justice Court" if rules else "small claims court"

    demand_sent = bool(details.demand_letter_sent)
    demand_event_date = details.demand_letter_date

    response_deadline = None
    if demand_sent and demand_event_date:
        response_deadline = demand_event_date + timedelta(days=demand_wait_days)

    def _completed_at(d: date | None) -> datetime | None:
        return datetime.combine(d, datetime.min.time(), tzinfo=timezone.utc) if d else None

    events = [
        TimelineEvent(
            case_id=uuid.UUID(case_id),
            event_type="demand_letter_required",
            title="Send a demand letter to your landlord",
            description="A written demand for the return of your deposit. This starts the clock on a bad-faith argument if your landlord doesn't respond.",
            event_date=demand_event_date,
            is_deadline=False,
            completed=demand_sent,
            completed_at=_completed_at(demand_event_date) if demand_sent else None,
            source="agent",
        ),
        TimelineEvent(
            case_id=uuid.UUID(case_id),
            event_type="deadline",
            title="Wait for your landlord's response",
            description=f"Texas courts treat continued silence after a demand letter as evidence of bad faith. Give your landlord {demand_wait_days} days to respond before filing.",
            event_date=response_deadline,
            is_deadline=True,
            completed=False,
            source="agent",
        ),
        TimelineEvent(
            case_id=uuid.UUID(case_id),
            event_type="filing_required",
            title=f"File your petition in {court_name}",
            description="File a petition for the return of your security deposit (plus any penalty and statutory fees you're entitled to) in the county where the property is located.",
            event_date=None,
            is_deadline=False,
            completed=False,
            source="agent",
        ),
        TimelineEvent(
            case_id=uuid.UUID(case_id),
            event_type="service_required",
            title="Serve your landlord with the petition",
            description="Have your landlord formally served (certified mail, constable/sheriff, or personal service) and keep the proof of service.",
            event_date=None,
            is_deadline=False,
            completed=False,
            source="agent",
        ),
        TimelineEvent(
            case_id=uuid.UUID(case_id),
            event_type="hearing",
            title="Attend your hearing",
            description="Bring your lease, move-in/move-out evidence, communications, and proof of service to your scheduled hearing.",
            event_date=None,
            is_deadline=False,
            completed=False,
            source="agent",
        ),
    ]
    db.add_all(events)
    await db.flush()


def _build_summary(result: dict) -> str:
    strength = result["case_strength"]
    if strength == "no_case":
        return f"Assessment complete — {result['recommended_path']}"

    label = {"strong": "strong", "moderate": "moderate", "weak": "not yet ripe"}.get(strength, strength)
    recovery = f"${result['estimated_recovery_min']:,.2f} - ${result['estimated_recovery_max']:,.2f}"
    parts = [f"Assessment complete — your case looks {label}.", f"Estimated recovery range: {recovery}."]
    if result["findings_good"]:
        parts.append(result["findings_good"][0]["text"])
    if result["findings_bad"]:
        parts.append(result["findings_bad"][0]["text"])
    parts.append(result["recommended_path"])
    return " ".join(parts)
