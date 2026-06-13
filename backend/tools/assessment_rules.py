"""Case-assessment rule engine — pure Python, no external calls.

Per-state constants mirror the structure of `tools.deadline_calculator`:
statutory penalty amounts, penalty multipliers, jurisdiction limits, statutes
of limitations, and citation strings copied verbatim from the corresponding
`knowledge/state_law/<STATE>.md` file (§8/8a, §10, §13, §14 for TX). Only TX
is populated — other states fall back to a degraded assessment that doesn't
cite law it hasn't loaded.
"""

from __future__ import annotations

from datetime import date
from typing import Any

STATE_ASSESSMENT_RULES: dict[str, dict] = {
    "TX": {
        "statutory_penalty": 100.0,
        "max_penalty_multiplier": 3.0,
        "jurisdiction_limit": 20000.0,
        "limitations_years": 4,
        "demand_letter_wait_days": 14,
        "citations": {
            "return_deadline": "Tex. Prop. Code §§ 92.103, 92.107",
            "forwarding_address": "Tex. Prop. Code § 92.107",
            "itemization": "Tex. Prop. Code § 92.104",
            "bad_faith": "Tex. Prop. Code § 92.109",
            "wear_and_tear": "Tex. Prop. Code § 92.001 et seq. — court-established standard",
            "limitations": "Tex. Civ. Prac. & Rem. Code § 16.004",
            "jurisdiction": "Texas Justice Court — $20,000 limit",
        },
        "wear_and_tear_examples": {
            "normal": [
                "Small nail holes from hanging pictures",
                "Minor scuffs on walls from furniture placement",
                "Carpet wear in high-traffic areas from normal use",
                "Faded paint from sunlight exposure",
                "Loose door handles from regular use",
            ],
            "damage": [
                "Large holes in walls",
                "Stains on carpet from pets or spills",
                "Broken fixtures or appliances from misuse",
                "Burns on countertops or floors",
                "Missing or broken blinds",
            ],
        },
    }
}

_BAD_FAITH_TEXT = {
    "complete_silence": "Your landlord has not returned your deposit, sent an itemization, or communicated with you since the return deadline passed.",
    "no_itemization_despite_withholding": "Your landlord withheld part of your deposit without sending a written itemization of deductions.",
    "late_itemization": "Your landlord's itemization was sent after the return deadline.",
    "demand_ignored": "Your landlord did not respond to your written demand letter within the recommended waiting period.",
}


def evaluate_assessment(details: Any, lease: Any, rules: dict | None, state: str | None) -> dict:
    """Evaluate a case against the rules for `state` (or a degraded baseline).

    `details` is a `CaseDetailsSecurityDeposit` row, `lease` is a
    `LeaseParseResult` row (or `None`). Returns a dict matching the
    "Output schema written to database" in the Phase 4 spec — callers are
    responsible for persisting the values onto `details`.
    """
    rules = rules or {}
    citations: dict[str, str] = rules.get("citations", {})
    statutory_penalty: float = rules.get("statutory_penalty", 0.0)
    max_multiplier: float = rules.get("max_penalty_multiplier", 1.0)
    jurisdiction_limit: float | None = rules.get("jurisdiction_limit")
    limitations_years: int | None = rules.get("limitations_years")
    demand_wait_days: int = rules.get("demand_letter_wait_days", 14)

    deposit_amount = float(details.deposit_amount or 0)
    amount_returned = float(details.amount_returned or 0)
    unpaid = max(deposit_amount - amount_returned, 0.0)
    forwarding_proof = bool(details.forwarding_address_proof)
    violation_confirmed: bool | None = details.violation_confirmed

    findings_good: list[dict] = []
    findings_caution: list[dict] = []
    findings_bad: list[dict] = []
    defenses_likely: list[dict] = []
    bad_faith_indicators: list[str] = []

    if not rules:
        findings_caution.append(
            {
                "text": f"Detailed {state or 'your state'} security-deposit law isn't loaded yet.",
                "explanation": "This assessment uses general deadline logic only — recovery estimates, penalty multipliers, and statutory citations aren't available for this state yet.",
            }
        )

    # RULE 003 — no forwarding address pauses the return-deadline clock.
    if not forwarding_proof:
        violation_confirmed = False
        explanation = "Until you give your landlord a forwarding address in writing, the return-deadline clock doesn't start."
        if citations.get("forwarding_address"):
            explanation += f" ({citations['forwarding_address']})"
        findings_caution.append({"text": "No proof of forwarding address on file", "explanation": explanation})
        defenses_likely.append(
            {
                "defense": "Tenant did not provide a forwarding address",
                "landlord_burden": "None — this pauses the return deadline entirely until an address is provided.",
                "tenant_response": "Provide any evidence of written address submission — email, text message, or certified letter.",
            }
        )

    case_strength: str | None = None
    recommended_path: str | None = None

    # No-case checks (first match wins).
    if deposit_amount > 0 and amount_returned >= deposit_amount and not violation_confirmed:
        case_strength = "no_case"
        recommended_path = "Your full deposit was returned before any return-deadline violation occurred — there's nothing to pursue right now."
    elif not forwarding_proof and not violation_confirmed:
        case_strength = "no_case"
        recommended_path = "Send your landlord a written forwarding address. Until then, the landlord owes nothing and there's no deadline violation to act on."
    elif limitations_years and details.move_out_date and (date.today() - details.move_out_date).days > limitations_years * 365:
        case_strength = "no_case"
        note = f"The statute of limitations ({limitations_years} years"
        if citations.get("limitations"):
            note += f", {citations['limitations']}"
        note += ") has likely expired for this claim."
        recommended_path = note

    if case_strength != "no_case":
        if violation_confirmed:
            findings_good.append(
                {
                    "text": f"Your landlord missed the security-deposit return deadline ({details.days_overdue or 0} days overdue).",
                    "statute": citations.get("return_deadline", ""),
                }
            )
        if forwarding_proof:
            findings_good.append(
                {
                    "text": "You have proof you provided your landlord a forwarding address.",
                    "statute": citations.get("forwarding_address", ""),
                }
            )
        if details.demand_letter_sent:
            findings_good.append(
                {
                    "text": "You've sent a written demand letter — continued silence after this strengthens a bad-faith argument.",
                    "statute": citations.get("bad_faith", ""),
                }
            )

        # Bad-faith indicators (§8a) — only computed where citation data is loaded.
        if rules:
            if violation_confirmed and details.landlord_communication == "none":
                bad_faith_indicators.append("complete_silence")
            if violation_confirmed and amount_returned < deposit_amount and not details.itemization_received:
                bad_faith_indicators.append("no_itemization_despite_withholding")
            if (
                details.itemization_received
                and details.itemization_date
                and details.deadline_date
                and details.itemization_date > details.deadline_date
            ):
                bad_faith_indicators.append("late_itemization")
            if (
                details.demand_letter_sent
                and details.demand_letter_date
                and (date.today() - details.demand_letter_date).days >= demand_wait_days
                and details.landlord_communication == "none"
            ):
                bad_faith_indicators.append("demand_ignored")

            for indicator in bad_faith_indicators:
                impact = f"Strengthens your bad-faith claim — eligible for up to {max_multiplier:g}x the deposit"
                if statutory_penalty:
                    impact += f" plus a ${statutory_penalty:,.0f} statutory penalty"
                if citations.get("bad_faith"):
                    impact += f" ({citations['bad_faith']})"
                impact += "."
                findings_bad.append({"text": _BAD_FAITH_TEXT[indicator], "impact": impact})

        # Defenses likely (§14) — citation-specific defenses are TX-only.
        if rules:
            if unpaid > 0:
                defenses_likely.append(
                    {
                        "defense": "Tenant caused damage beyond normal wear and tear",
                        "landlord_burden": "Must provide an itemized list of deductions with dollar amounts and, ideally, receipts.",
                        "tenant_response": "Challenge each item against your move-in inspection report and the normal wear-and-tear definitions.",
                    }
                )
            if not details.itemization_received:
                defenses_likely.append(
                    {
                        "defense": "Landlord claims the itemization was sent on time",
                        "landlord_burden": "Must produce proof of mailing within the deadline — the postmark date controls, not the receipt date.",
                        "tenant_response": "Request proof of mailing. If your landlord can't produce it, the date you actually received it controls and the itemization is considered late.",
                    }
                )
            flagged = (getattr(lease, "flagged_clauses", None) or []) if lease is not None else []
            if any("clean" in f"{c.get('clause', '')} {c.get('concern', '')}".lower() for c in flagged):
                defenses_likely.append(
                    {
                        "defense": "A cleaning clause in your lease authorizes the deduction",
                        "landlord_burden": "Must show actual cleaning costs with receipts — blanket 'professional cleaning' clauses are routinely rejected by Texas courts.",
                        "tenant_response": "Argue the clause is unenforceable as written and request receipts for the actual cleaning costs.",
                    }
                )

        # Wear and tear (§7a) — only when an itemization exists to evaluate.
        if rules and details.itemization_received:
            normal_examples = rules.get("wear_and_tear_examples", {}).get("normal", [])
            if normal_examples:
                explanation = "Texas courts generally treat these as normal wear and tear, not deductible damage: " + "; ".join(normal_examples) + "."
                if citations.get("wear_and_tear"):
                    explanation += f" ({citations['wear_and_tear']})"
                findings_caution.append(
                    {"text": "Review your landlord's itemized deductions against normal wear and tear.", "explanation": explanation}
                )

    # Recovery range (§8/8a).
    if rules:
        if bad_faith_indicators:
            penalty_multiplier = max_multiplier
            recovery_max = unpaid * max_multiplier + statutory_penalty
        else:
            penalty_multiplier = 1.0
            recovery_max = unpaid
        recovery_min = unpaid
        if unpaid == 0 and case_strength != "no_case":
            recovery_min = 0.0
            recovery_max = statutory_penalty if bad_faith_indicators else 0.0
    else:
        penalty_multiplier = 1.0
        recovery_min = unpaid
        recovery_max = unpaid

    # Jurisdiction limit (RULE 005).
    exceeds_jurisdiction: bool | None = None
    jurisdiction_options: list[str] | None = None
    if jurisdiction_limit is not None:
        exceeds_jurisdiction = recovery_max > jurisdiction_limit
        if exceeds_jurisdiction:
            jurisdiction_options = [
                f"Waive the amount above ${jurisdiction_limit:,.0f} and file in Justice Court.",
                "File in County Court at Law instead — an attorney is strongly recommended.",
            ]
            findings_caution.append(
                {
                    "text": f"Your estimated recovery (${recovery_max:,.2f}) exceeds the ${jurisdiction_limit:,.0f} Justice Court limit.",
                    "explanation": "You'll need to choose between waiving the excess or filing in a higher court.",
                }
            )

    # Notice compliance (RULE 006) — TX only.
    notice_compliant: bool | None = None
    notice_risk_amount: float | None = None
    if rules:
        if lease is not None and getattr(lease, "notice_compliant", None) is not None:
            notice_compliant = lease.notice_compliant
        elif details.notice_days is not None and details.lease_required_notice_days is not None:
            notice_compliant = details.notice_days >= details.lease_required_notice_days
        if notice_compliant is False:
            findings_caution.append(
                {
                    "text": "You may not have given your landlord the move-out notice your lease requires.",
                    "explanation": "Insufficient notice can give your landlord grounds to claim lost-rent damages, which could offset your deposit claim. The exact amount depends on your lease's rent terms.",
                }
            )

    # Case strength (when not already no_case).
    if case_strength is None:
        if violation_confirmed and bad_faith_indicators:
            case_strength = "strong"
        elif violation_confirmed:
            case_strength = "moderate"
        elif unpaid > 0:
            case_strength = "weak"
        else:
            case_strength = "no_case"
            recommended_path = "There's no deposit currently owed and no return-deadline violation — there's nothing to pursue right now."

    if recommended_path is None:
        if case_strength == "weak":
            if not forwarding_proof:
                recommended_path = "Send your landlord a written forwarding address. Once the return deadline passes after that without a refund or itemization, you'll have a confirmed violation."
            else:
                recommended_path = "The return deadline hasn't passed yet. Once it does without a refund or itemization, you'll have a confirmed violation and can proceed."
        else:
            court_name = "Justice Court" if rules else "small claims court"
            recommended_path = f"Send a demand letter, then file in {court_name} if your landlord doesn't respond within {demand_wait_days} days."

    return {
        "violation_confirmed": violation_confirmed,
        "bad_faith_indicators": bad_faith_indicators,
        "case_strength": case_strength,
        "findings_good": findings_good,
        "findings_caution": findings_caution,
        "findings_bad": findings_bad,
        "defenses_likely": defenses_likely,
        "estimated_recovery_min": round(recovery_min, 2),
        "estimated_recovery_max": round(recovery_max, 2),
        "penalty_multiplier": penalty_multiplier,
        "exceeds_jurisdiction": exceeds_jurisdiction,
        "jurisdiction_options": jurisdiction_options,
        "recommended_path": recommended_path,
        "notice_compliant": notice_compliant,
        "notice_risk_amount": notice_risk_amount,
    }


def compute_strength_bars(details: Any, lease_parsed: bool = False) -> dict:
    """Compute the four 0-100 strength bars for the assessment hero section.

    Cheap to recompute from persisted fields — not stored.
    """
    if details.violation_confirmed:
        violation_clear = 100
    elif details.case_strength == "weak":
        violation_clear = 50
    else:
        violation_clear = 0

    bad_faith_count = len(details.bad_faith_indicators or [])
    bad_faith_case = min(bad_faith_count / 4 * 100, 100)

    evidence_flags = [
        bool(details.forwarding_address_proof),
        lease_parsed,
        bool(details.landlord_sos_verified),
        bool(details.itemization_received),
    ]
    evidence_quality = sum(evidence_flags) / len(evidence_flags) * 100

    procedural_risk = 100
    if details.notice_compliant is False:
        procedural_risk -= 30
    if details.exceeds_jurisdiction:
        procedural_risk -= 20
    if not details.landlord_sos_verified:
        procedural_risk -= 20
    procedural_risk = max(procedural_risk, 0)

    return {
        "violation_clear": violation_clear,
        "bad_faith_case": round(bad_faith_case),
        "evidence_quality": round(evidence_quality),
        "procedural_risk": procedural_risk,
    }
