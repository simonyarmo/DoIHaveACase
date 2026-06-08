# Phase 2 — State law markdown schema and Texas reference file

## Schema rules

Every state law file must follow this exact structure. Field order, heading names, and section numbers are fixed. The agent parser depends on consistent locations — do not rename or reorder sections.

Every file begins with a header block:

```markdown
# [STATE_ABBR] — Security Deposit Law
## Last Verified: [YYYY-MM-DD]
## Source: [OFFICIAL_URL]
## Next Review Due: [YYYY-MM-DD]
## Status: [active | stub | pending_review]
```

---

## Full Texas reference file (TX.md)

```markdown
# TX — Security Deposit Law
## Last Verified: 2025-01-15
## Source: https://statutes.capitol.texas.gov/Docs/PR/htm/PR.92.htm
## Next Review Due: 2026-01-15
## Status: active

---

## 1. STATUTE REFERENCE
- Primary: Texas Property Code § 92.101 – § 92.109
- Related: § 92.001 (definitions), § 92.056 (repair and remedy)

---

## 2. DEPOSIT LIMITS
- Maximum allowed: No statutory maximum
- Notes: Amount must be stated in the lease agreement

---

## 3. HOLDING REQUIREMENTS
- Must be held in separate account: No statutory requirement
- Interest bearing required: No
- Tenant must be notified of account: No
- Notes: Landlord may commingle deposit with other funds

---

## 4. MOVE-OUT NOTICE REQUIREMENTS
- Written notice required: Lease-dependent
- Notice period: Typically 30–60 days — check lease
- Notice period source: Lease agreement not statute
- Method required: As specified in lease
- Notes: Failure to provide required notice may give landlord grounds to deduct lost rent. Lease parser must extract this clause specifically.

---

## 5. RETURN DEADLINE
- Days to return: 30
- Deadline trigger: Date tenant surrenders premises AND provides written forwarding address — both required
- Forwarding address required: Yes — § 92.107
- Effect of no forwarding address: Landlord not required to return deposit until forwarding address provided. Penalty provisions still apply once address is given and 30 days pass.

---

## 6. ITEMIZATION REQUIREMENTS
- Written itemization required: Yes — § 92.104
- Must accompany return: Yes — within same 30-day deadline
- Required contents:
  - Description of each deduction: Yes
  - Dollar amount per deduction: Yes
  - Receipts required: No — but strongly recommended by courts
- Delivery method: Must be sent to forwarding address provided

---

## 7. ALLOWABLE DEDUCTIONS
- Unpaid rent: Yes
- Damage beyond normal wear and tear: Yes
- Cleaning if specified in lease: Yes — if clause is specific not blanket. Courts reject "professional cleaning regardless of condition" clauses as unenforceable.
- Lease break fees: Yes — if specified in lease
- Unpaid utilities: Yes — if specified in lease

## 7a. WEAR AND TEAR DEFINITION
- Statutory definition: Not explicitly defined in statute
- Court-established standard: Deterioration from ordinary use over time without negligence or abuse
- Common examples courts have ruled as normal wear and tear:
  - Small nail holes from hanging pictures
  - Minor scuffs on walls from furniture placement
  - Carpet wear in high-traffic areas from normal use
  - Faded paint from sunlight exposure
  - Loose door handles from regular use
- Common examples courts have ruled as actual damage:
  - Large holes in walls
  - Stains on carpet from pets or spills
  - Broken fixtures or appliances from misuse
  - Burns on countertops or floors
  - Missing or broken blinds

---

## 8. PENALTIES FOR WRONGFUL WITHHOLDING
- Penalty multiplier: Up to 3x — § 92.109
- Multiplier trigger: Bad faith retention
- Statutory penalty: $100 — § 92.109(a)
- Attorney fees: Yes — if tenant prevails — § 92.109(a)
- Burden of proof: Tenant must prove bad faith

## 8a. BAD FAITH DEFINITION
- Statutory definition: Not explicitly defined
- Court-established indicators:
  - Complete silence — no return, no itemization, no communication after deadline
  - Deductions taken without receipts or supporting documentation
  - Itemization sent after the 30-day deadline
  - Deductions for items that are clearly normal wear and tear
  - Landlord aware of violation and chose not to remedy
  - Pattern of similar complaints from other tenants

---

## 9. DEMAND LETTER
- Legally required before filing: No
- Strongly recommended: Yes
- Effect on bad faith argument: Significantly strengthens — continued silence after formal written demand is treated as strong evidence of bad faith by Texas courts
- Recommended waiting period after sending: 14 days

---

## 10. FILING INFORMATION
- Court: Justice Court (small claims)
- Maximum claim amount: $20,000
- Where to file: County where the property is located
- Filing fee range: $54 – $100 depending on precinct
- Statute of limitations: 4 years — Texas Civil Practice and Remedies Code § 16.004
- Online filing available: Some counties — Harris County has online filing portal

---

## 11. SERVICE OF PROCESS
- Acceptable methods:
  - Certified mail: Yes
  - Constable or Sheriff: Yes — fee typically $75–$100
  - Personal service: Yes
- Who can serve: Constable, sheriff, or any person over 18 not a party to the case
- Proof of service required: Yes — Return of Service form

---

## 12. LOCAL VARIATIONS
- Counties with known local rules:
  - Harris County: Online filing available, 8 Justice Court precincts — file in precinct where property is located
  - Travis County: Mediation strongly encouraged before hearing, some courts offer free mediation
- Cities with additional tenant protections:
  - Austin: Austin City Code § 4-14 — additional retaliation protections, does not extend deposit deadline
  - Houston: No additional local deposit protections beyond state law

---

## 13. AGENT DECISION RULES

RULE 001:
  IF days_since_moveout > 30
  AND no_deposit_returned = true
  AND no_itemization_sent = true
  THEN violation_confirmed = true

RULE 002:
  IF violation_confirmed = true
  AND landlord_provided_no_communication = true
  THEN bad_faith_indicator = true

RULE 003:
  IF forwarding_address_not_provided = true
  THEN return_deadline_clock = paused
  AND penalty_eligibility MAY be reduced
  AND agent MUST flag this to user as case risk

RULE 004:
  IF damage_claimed_by_landlord = true
  THEN agent MUST evaluate:
    - Was damage documented on move-in report?
    - Does damage exceed normal wear and tear per section 7a?
    - Did landlord provide receipts?

RULE 005:
  IF deposit_amount + penalties > 20000
  THEN agent MUST notify user of two options:
    - Option A: Waive amount above $20,000 and file in Justice Court
    - Option B: File in County Court at Law — attorney strongly recommended

RULE 006:
  IF lease_required_notice_days IS NOT NULL
  AND notice_days_provided < lease_required_notice_days
  THEN agent MUST calculate:
    - Days short of required notice
    - Lost rent exposure to landlord
    - Whether this offsets deposit claim

---

## 14. COMMON LANDLORD DEFENSES

DEFENSE 1: Tenant caused damage
  Landlord burden: Must provide itemized list with dollar amounts and receipts
  Tenant response: Challenge each item against move-in report and wear and tear definitions in section 7a

DEFENSE 2: Tenant did not provide forwarding address
  Effect in Texas: Pauses the 30-day deadline clock entirely
  Tenant response: Provide any evidence of written address submission — email, text, certified letter

DEFENSE 3: We mailed the itemization on time
  Court standard: Postmark date controls not receipt date
  Tenant response: Request proof of mailing — if landlord cannot produce it, filing date controls

DEFENSE 4: Cleaning clause in lease authorizes deduction
  Court standard: Blanket cleaning clauses routinely rejected by Texas courts — must be actual costs with receipts
  Tenant response: Argue clause is unenforceable, request receipts for actual cleaning costs

---

## 15. REVISION HISTORY

| Date       | Change          | Source                          | Verified By |
|------------|-----------------|---------------------------------|-------------|
| 2025-01-15 | Initial entry   | statutes.capitol.texas.gov      | Pipeline    |
```

---

## Stub template for CA.md and FL.md

```markdown
# [STATE] — Security Deposit Law
## Last Verified: pending
## Source: pending
## Next Review Due: pending
## Status: stub

This state has not yet been fully ingested.
The ingestion pipeline will populate this file
on the first on-demand request for this state.

All sections below are placeholders.

## 1. STATUTE REFERENCE
- Primary: pending
## 2. DEPOSIT LIMITS
- pending
## 3. HOLDING REQUIREMENTS
- pending
## 4. MOVE-OUT NOTICE REQUIREMENTS
- pending
## 5. RETURN DEADLINE
- Days to return: pending
## 6. ITEMIZATION REQUIREMENTS
- pending
## 7. ALLOWABLE DEDUCTIONS
- pending
## 8. PENALTIES FOR WRONGFUL WITHHOLDING
- pending
## 9. DEMAND LETTER
- pending
## 10. FILING INFORMATION
- pending
## 11. SERVICE OF PROCESS
- pending
## 12. LOCAL VARIATIONS
- pending
## 13. AGENT DECISION RULES
- pending
## 14. COMMON LANDLORD DEFENSES
- pending
## 15. REVISION HISTORY
| Date | Change | Source | Verified By |
|------|--------|--------|-------------|
```
