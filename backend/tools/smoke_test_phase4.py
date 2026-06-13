"""Phase 4 smoke test — case assessment agent and law application engine.

Run from `backend/` with the venv active:

    python tools/smoke_test_phase4.py

Exercises (without needing a running uvicorn server or Celery worker):
  - POST /cases + PATCH /cases/{case_id} -> a TX fixture matching the Phase 4
    spec's "strong" example (deposit 1500, returned 0, violation confirmed,
    no itemization, no landlord communication).
  - POST /cases/{case_id}/submit + agents.intake_agent._run(...) -> Phase 4
    chains agents.assessment_agent._run(...) in-process after research, so
    this exercises the full pipeline: case.status -> action_plan,
    case_strength == "strong", estimated_recovery_min/max == 1500 / 4600
    (1500 * 3x penalty multiplier + $100 statutory penalty), and a 5-step
    agent-generated action plan in timeline_events.
  - GET /cases (list), GET /cases/{case_id}/assessment, POST
    /cases/{case_id}/assessment/refresh (queue-only — no worker required).
  - POST/GET/PUT/DELETE /cases/{case_id}/expenses.
  - tools.assessment_rules.evaluate_assessment(...) called directly with
    hand-built fixtures for each no-case branch (full return before
    violation, no forwarding address, statute of limitations expired) and
    the degraded non-TX path.

Cleanup deletes the test case's `lease_parse_results` row(s) (no ON DELETE
CASCADE from `cases`), then the `cases` row (cascades everything else).

Requires AZURE_*, SUPABASE_*, and CELERY_* settings in `backend/.env`
(same as the running app), plus a reachable Redis instance for
`progress_bus` and the Celery broker.
"""

import asyncio
import sys
import time
import uuid
from datetime import date, timedelta
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from httpx import ASGITransport, AsyncClient
from jose import jwt
from sqlalchemy import delete, select

from agents import intake_agent
from config import settings
from database import async_session_factory
from main import app
from models.case import Case
from models.case_detail import CaseDetailsSecurityDeposit
from models.lease_parse import LeaseParseResult
from models.timeline import TimelineEvent
from tools.assessment_rules import STATE_ASSESSMENT_RULES, evaluate_assessment

results: list[tuple[str, bool, str]] = []

ACTION_PLAN_SEQUENCE = ["demand_letter_required", "deadline", "filing_required", "service_required", "hearing"]


def check(name: str, ok: bool, detail: str = "") -> None:
    results.append((name, ok, detail))
    status = "PASS" if ok else "FAIL"
    print(f"[{status}] {name}" + (f" - {detail}" if detail else ""))


def make_token() -> str:
    return jwt.encode(
        {
            "sub": "00000000-0000-0000-0000-000000000001",
            "email": "smoke-test@example.com",
            "aud": "authenticated",
            "exp": int(time.time()) + 3600,
        },
        settings.supabase_jwt_secret,
        algorithm="HS256",
    )


def make_details(**overrides: object) -> SimpleNamespace:
    """Minimal stand-in for a `CaseDetailsSecurityDeposit` row covering every
    attribute `evaluate_assessment` reads. Defaults describe a confirmed
    violation with proof of forwarding address and no landlord response."""
    base: dict[str, object] = dict(
        deposit_amount=1500,
        amount_returned=0,
        forwarding_address_proof=True,
        violation_confirmed=True,
        days_overdue=30,
        demand_letter_sent=False,
        demand_letter_date=None,
        landlord_communication="none",
        itemization_received=False,
        itemization_date=None,
        deadline_date=date.today() - timedelta(days=30),
        move_out_date=date.today() - timedelta(days=60),
        notice_days=None,
        lease_required_notice_days=None,
    )
    base.update(overrides)
    return SimpleNamespace(**base)


def run_rule_engine_checks() -> None:
    """Direct `evaluate_assessment(...)` checks — no DB or HTTP involved."""
    tx_rules = STATE_ASSESSMENT_RULES["TX"]

    # Full deposit returned before any deadline violation -> no_case, $0 range.
    result = evaluate_assessment(make_details(amount_returned=1500, violation_confirmed=False), None, tx_rules, "TX")
    check("no-case: full return before violation -> case_strength=no_case", result["case_strength"] == "no_case", f"got {result['case_strength']}")
    check(
        "no-case: full return -> recovery range $0-$0",
        result["estimated_recovery_min"] == 0 and result["estimated_recovery_max"] == 0,
        f"got {result['estimated_recovery_min']}-{result['estimated_recovery_max']}",
    )

    # No proof of forwarding address -> RULE 003 pauses the deadline clock -> no_case.
    result = evaluate_assessment(make_details(forwarding_address_proof=False, violation_confirmed=True), None, tx_rules, "TX")
    check("no-case: no forwarding address -> case_strength=no_case", result["case_strength"] == "no_case", f"got {result['case_strength']}")
    check("no-case: no forwarding address -> violation_confirmed overridden to False", result["violation_confirmed"] is False, f"got {result['violation_confirmed']}")
    check(
        "no-case: no forwarding address -> recommended_path mentions forwarding address",
        "forwarding address" in (result["recommended_path"] or "").lower(),
        f"got {result['recommended_path']!r}",
    )

    # Move-out date older than the statute of limitations -> no_case.
    result = evaluate_assessment(make_details(move_out_date=date.today() - timedelta(days=5 * 365)), None, tx_rules, "TX")
    check("no-case: statute of limitations expired -> case_strength=no_case", result["case_strength"] == "no_case", f"got {result['case_strength']}")
    check(
        "no-case: statute of limitations expired -> recommended_path cites limitations",
        "statute of limitations" in (result["recommended_path"] or "").lower(),
        f"got {result['recommended_path']!r}",
    )

    # Non-TX state -> degraded assessment: no penalty multiplier, no bad-faith indicators, no jurisdiction/notice checks.
    result = evaluate_assessment(make_details(), None, None, "CA")
    check("non-TX: degraded path -> case_strength=moderate (violation confirmed, no bad-faith data)", result["case_strength"] == "moderate", f"got {result['case_strength']}")
    check(
        "non-TX: degraded path -> recovery range == unpaid amount (no penalty)",
        result["estimated_recovery_min"] == 1500 and result["estimated_recovery_max"] == 1500,
        f"got {result['estimated_recovery_min']}-{result['estimated_recovery_max']}",
    )
    check(
        "non-TX: degraded path -> findings_caution notes state law isn't loaded",
        len(result["findings_caution"]) >= 1 and "CA" in result["findings_caution"][0]["text"],
        f"got {result['findings_caution']}",
    )
    check("non-TX: degraded path -> notice_compliant is None (no rules to check against)", result["notice_compliant"] is None, f"got {result['notice_compliant']}")


async def run_checks() -> str | None:
    """Run the full-pipeline checks in a single asyncio.run() / event loop.
    Returns the created case_id (for cleanup), or None if case creation
    itself failed.
    """
    token = make_token()
    headers = {"Authorization": f"Bearer {token}"}
    case_id: str | None = None
    session_id: str | None = None

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        r = await client.post("/cases", headers=headers)
        body = r.json() if r.status_code == 201 else {}
        check("POST /cases -> 201", r.status_code == 201, f"got {r.status_code} {body}")
        if r.status_code != 201:
            return None
        case_id = body["id"]

        # TX fixture matching the Phase 4 spec's "strong" example.
        move_out = date.today() - timedelta(days=60)
        patch_body = {
            "state": "TX",
            "county": "Harris",
            "details": {
                "property_address": "123 Main St, Houston, TX 77002",
                "property_state": "TX",
                "property_county": "Harris",
                "property_type": "apartment",
                "deposit_amount": 1500,
                "amount_returned": 0,
                "move_in_date": (move_out - timedelta(days=365)).isoformat(),
                "move_out_date": move_out.isoformat(),
                "keys_returned_date": move_out.isoformat(),
                "forwarding_address": "456 Oak St, Houston, TX 77003",
                "forwarding_address_proof": True,
                "landlord_communication": "none",
            },
        }
        r = await client.patch(f"/cases/{case_id}", headers=headers, json=patch_body)
        check("PATCH /cases/{case_id} -> 200", r.status_code == 200, f"got {r.status_code} {r.text}")

        r = await client.post(f"/cases/{case_id}/submit", headers=headers)
        body = r.json() if r.status_code == 200 else {}
        check("POST /cases/{case_id}/submit -> 200", r.status_code == 200, f"got {r.status_code} {body}")
        session_id = body.get("session_id")

    if session_id:
        try:
            await intake_agent._run(case_id, session_id)
            check("intake_agent._run completes without raising (chains assessment_agent)", True)
        except Exception as exc:  # noqa: BLE001
            check("intake_agent._run completes without raising (chains assessment_agent)", False, f"error: {exc}")

    async with async_session_factory() as db:
        case = await db.get(Case, uuid.UUID(case_id))
        check("case.status == action_plan", case is not None and case.status == "action_plan", f"got {case.status if case else None}")

        details = (
            await db.execute(select(CaseDetailsSecurityDeposit).where(CaseDetailsSecurityDeposit.case_id == uuid.UUID(case_id)))
        ).scalar_one_or_none()
        check("details.case_strength == strong", details is not None and details.case_strength == "strong", f"got {details.case_strength if details else None}")
        check(
            "details.estimated_recovery_min == 1500",
            details is not None and float(details.estimated_recovery_min) == 1500.0,
            f"got {details.estimated_recovery_min if details else None}",
        )
        check(
            "details.estimated_recovery_max == 4600 (1500 * 3x + $100 penalty)",
            details is not None and float(details.estimated_recovery_max) == 4600.0,
            f"got {details.estimated_recovery_max if details else None}",
        )
        check("details.bad_faith_indicators non-empty", details is not None and bool(details.bad_faith_indicators), f"got {details.bad_faith_indicators if details else None}")

        events = (
            await db.execute(
                select(TimelineEvent).where(TimelineEvent.case_id == uuid.UUID(case_id), TimelineEvent.source == "agent")
            )
        ).scalars().all()
        event_types = [e.event_type for e in events]
        check(
            "5 agent-generated timeline_events in the expected sequence",
            event_types == ACTION_PLAN_SEQUENCE,
            f"got {event_types}",
        )

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # --- GET /cases (Dashboard list) ---
        r = await client.get("/cases", headers=headers)
        body = r.json() if r.status_code == 200 else []
        check("GET /cases -> 200", r.status_code == 200, f"got {r.status_code}")
        summary = next((c for c in body if c.get("id") == case_id), None)
        check(
            "GET /cases includes this case with case_strength=strong",
            summary is not None and summary.get("case_strength") == "strong",
            f"got {summary}",
        )

        # --- GET /cases/{case_id}/assessment ---
        r = await client.get(f"/cases/{case_id}/assessment", headers=headers)
        body = r.json() if r.status_code == 200 else {}
        check("GET /cases/{case_id}/assessment -> 200", r.status_code == 200, f"got {r.status_code} {body}")
        check(
            "assessment.strength_bars has all four bars",
            set(body.get("strength_bars", {}).keys()) == {"violation_clear", "bad_faith_case", "evidence_quality", "procedural_risk"},
            f"got {body.get('strength_bars')}",
        )
        check(
            "assessment.timeline_events in fixed action-plan order",
            [e.get("event_type") for e in body.get("timeline_events", [])] == ACTION_PLAN_SEQUENCE,
            f"got {[e.get('event_type') for e in body.get('timeline_events', [])]}",
        )

        # --- POST /cases/{case_id}/assessment/refresh (queue-only) ---
        r = await client.post(f"/cases/{case_id}/assessment/refresh", headers=headers)
        body = r.json() if r.status_code == 202 else {}
        check("POST /cases/{case_id}/assessment/refresh -> 202", r.status_code == 202, f"got {r.status_code} {body}")
        check("refresh returns status=queued", body.get("status") == "queued", f"got {body}")

        # --- expenses CRUD ---
        r = await client.post(
            f"/cases/{case_id}/expenses",
            headers=headers,
            json={"description": "Filing fee", "amount": 54.0, "date": date.today().isoformat(), "category": "filing_fee", "recoverable": True},
        )
        body = r.json() if r.status_code == 201 else {}
        check("POST /cases/{case_id}/expenses -> 201", r.status_code == 201, f"got {r.status_code} {body}")
        expense_id = body.get("id")

        r = await client.get(f"/cases/{case_id}/expenses", headers=headers)
        body = r.json() if r.status_code == 200 else []
        check(
            "GET /cases/{case_id}/expenses -> 200 includes new expense",
            r.status_code == 200 and any(e.get("id") == expense_id for e in body),
            f"got {r.status_code} {body}",
        )

        r = await client.put(f"/cases/{case_id}/expenses/{expense_id}", headers=headers, json={"amount": 60.0})
        body = r.json() if r.status_code == 200 else {}
        check("PUT /cases/{case_id}/expenses/{expense_id} -> 200 updates amount", r.status_code == 200 and body.get("amount") == 60.0, f"got {r.status_code} {body}")

        r = await client.delete(f"/cases/{case_id}/expenses/{expense_id}", headers=headers)
        check("DELETE /cases/{case_id}/expenses/{expense_id} -> 204", r.status_code == 204, f"got {r.status_code}")

    return case_id


async def cleanup(case_id: str | None) -> None:
    if case_id is None:
        return

    async with async_session_factory() as db:
        await db.execute(delete(LeaseParseResult).where(LeaseParseResult.case_id == uuid.UUID(case_id)))
        case = await db.get(Case, uuid.UUID(case_id))
        if case is not None:
            await db.delete(case)
        await db.commit()


async def run_async_checks() -> None:
    case_id = await run_checks()
    await cleanup(case_id)


def main() -> int:
    run_rule_engine_checks()
    asyncio.run(run_async_checks())

    failed = [name for name, ok, _ in results if not ok]
    print()
    print(f"{len(results) - len(failed)}/{len(results)} checks passed")
    if failed:
        print("FAILED:")
        for name in failed:
            print(f"  - {name}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
