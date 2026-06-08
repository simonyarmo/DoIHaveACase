# Phase 4 — Case assessment agent and law application engine

## Goal
Build the reasoning engine that evaluates a user's case against state law and produces an honest, structured assessment. By the end of this phase the assessment screen is fully populated with findings, strength indicators, recovery estimates, and a clear action plan.

## What to build

### 1. Assessment agent
`backend/agents/assessment_agent.py`

Triggered automatically when intake research completes (end of Phase 3 pipeline). Can also be re-triggered manually if new evidence is added.

The agent queries the case Foundry IQ knowledge base and the state law knowledge base together. It never invents law — every finding must cite a specific section of the loaded state law file.

**Input:** all fields from `case_details_security_deposit`, lease parse results, uploaded evidence list

**Process:**
1. Query `kb-state-law-security-deposit` for this state — load all decision rules from section 13
2. Apply each RULE against actual case data
3. Evaluate each COMMON LANDLORD DEFENSE from section 14 against evidence
4. Assess wear and tear claims against section 7a definitions
5. Calculate recovery range (minimum = deposit only, maximum = deposit + penalty multiplier + statutory penalty)
6. Check jurisdiction limit — flag if total exceeds small claims maximum
7. Evaluate notice compliance using `lease_required_notice_days` vs `notice_days`
8. Produce structured findings with confidence levels
9. Write assessment to `case_details_security_deposit` computed fields
10. Write finding summaries to `conversation_messages` as agent message
11. Update case status to `action_plan`

**Output schema written to database:**
```python
{
  "violation_confirmed": bool,
  "bad_faith_indicators": [str],
  "case_strength": "strong" | "moderate" | "weak" | "no_case",
  "findings_good": [{"text": str, "statute": str}],
  "findings_caution": [{"text": str, "explanation": str}],
  "findings_bad": [{"text": str, "impact": str}],
  "defenses_likely": [{"defense": str, "landlord_burden": str, "tenant_response": str}],
  "estimated_recovery_min": float,
  "estimated_recovery_max": float,
  "penalty_multiplier": float,
  "exceeds_jurisdiction": bool,
  "jurisdiction_options": [str] | null,
  "recommended_path": str,
  "notice_compliant": bool | null,
  "notice_risk_amount": float | null
}
```

### 2. Honest case assessment — no case path
The agent must be willing to return `case_strength: "no_case"` and explain clearly why. This triggers a different UI state than the normal assessment screen.

No-case conditions to check:
- Deposit was returned in full within the legal deadline
- Forwarding address was never provided and landlord has no other obligation yet
- Legitimate documented damage clearly exceeds deposit amount
- Statute of limitations has expired
- Tenant materially breached the lease in a way that offsets the claim

When no-case is returned, the agent produces a clear explanation of why and suggests alternatives — demand negotiation, mediation, or what would need to change for a case to exist.

### 3. Assessment API endpoint
```
GET /cases/{case_id}/assessment
```
Returns the structured assessment output. Called by the frontend assessment screen on load.

```
POST /cases/{case_id}/assessment/refresh
```
Re-runs the assessment agent — used when new evidence is added or case details are updated.

### 4. Action plan generator
After assessment, the agent builds a sequential action plan stored as `timeline_events`.

For a strong or moderate case:
```
Step 1: Send demand letter       → event_type: demand_letter_required
Step 2: Wait for response        → event_type: deadline (14 days from send date)
Step 3: File petition            → event_type: filing_required (locked until step 2 deadline passes)
Step 4: Serve defendant          → event_type: service_required (locked until filing)
Step 5: Attend hearing           → event_type: hearing (locked until served)
```

Each event includes:
- `title` and `description`
- `is_deadline` flag where applicable
- `document_id` link where a document is required
- `source: agent`

The action plan is what powers the timeline screen in Phase 6.

### 5. Assessment screen — frontend
Refer to the UI mockup for component placement and design language.

**Hero section:**
- Recovery range (min – max formatted as currency)
- Case strength badge (strong / moderate / weak / no case)
- Strength breakdown bars (violation clear, bad faith case, evidence quality, procedural risk) — percentages calculated from assessment output

**Findings section:**
- Green rows for strengths — each cites the specific statute
- Amber rows for cautions — each explains the risk and how to address it
- Red rows for weaknesses — shown only when they exist

**Defenses section:**
- Each likely landlord defense shown with what they must prove and how the tenant counters it

**No-case state:**
- Replace hero with a clear explanation panel
- List specific reasons why
- Show what alternatives exist
- Show what would need to change for a case to become viable

**Action plan section:**
- Sequential steps with locked/unlocked state
- Each step links to the relevant document or instruction

### 6. Expense tracker — frontend component
Appears on the dashboard and case summary sidebar.

Users can manually log expenses:
- Description, amount, date, category (filing fee / service fee / mail / notary / other)
- Optional: attach a receipt document
- `recoverable` flag — defaults to true, user can uncheck

Running total of recoverable expenses displayed in:
- Dashboard stat cell (replaces "total at stake")
- Case summary sidebar panel
- Feeds into petition and default judgment document generation (Phase 5)

API endpoints:
```
POST /cases/{case_id}/expenses
GET  /cases/{case_id}/expenses
PUT  /cases/{case_id}/expenses/{expense_id}
DELETE /cases/{case_id}/expenses/{expense_id}
```

## Definition of done
- [ ] Assessment agent runs to completion for a Texas test case with known data
- [ ] All decision rules from TX.md section 13 are correctly applied
- [ ] Wear and tear evaluation correctly handles edge cases from TX.md section 7a
- [ ] No-case path returns correct output and triggers different UI state
- [ ] Recovery range calculation is correct — verify against manual calculation
- [ ] Action plan timeline events are created in correct order with correct lock states
- [ ] Assessment screen displays all sections from mockup correctly
- [ ] Case strength bars calculate correctly from assessment output
- [ ] Expense tracker accepts entries and running total is correct
- [ ] Recoverable expense total appears in dashboard stat cell

## What is NOT in this phase
- Document generation (Phase 5)
- Timeline UI with full event rendering (Phase 6)
- SMS alerts on assessment complete (Phase 6)
