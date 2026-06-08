# Phase 5 — Document studio, template engine, and inline comments

## Goal
Build the document generation system. Users manually trigger document creation from the action plan. The template engine fills each document from verified case data, the document agent generates inline comments for every changed or uncertain field, and the user must resolve all comments before exporting. All documents are stored and versioned.

## What to build

### 1. Template engine
`backend/documents/template_engine.py`

Reads YAML template definitions from `kb-document-templates` in Foundry IQ. For each document type, pulls all required field values from the case record, case details, parties, evidence, and state law knowledge base.

**Process:**
1. Load template definition for requested document type
2. Run preflight checks — verify all required fields and prior documents exist
3. If preflight fails, return list of blocking issues to frontend (not an error — tells user what is missing)
4. For each field in the template, resolve the value from its `value_source`
5. Identify fields that need agent comments — `agent_comment: always` or `agent_comment_if` condition is true
6. Pass flagged fields to comment engine
7. Assemble the complete document as structured HTML
8. Store HTML and field map to Azure Blob Storage
9. Create `documents` record with status `draft`
10. Create all `document_comments` records
11. Return document ID and comment count to frontend

**State variation handling:**
Before filling fields, the template engine checks the case state against the `state_variations` section of the template. Applies any field overrides or additions before processing.

**Linked document generation:**
Some documents must generate together — `amended_petition` always generates with `motion_to_amend`. The template registry defines `generates_with` for these cases. Both documents are generated in a single call and returned as a package.

### 2. Comment engine
`backend/documents/comment_engine.py`

For each field flagged for a comment, the agent generates the comment text. Comments are grounded in the case Foundry IQ knowledge base — the agent references actual case data and actual state law in every comment.

**Three comment types:**
- `changed` — agent modified the value from what was entered. Explains why using statute or SOS data.
- `clarification` — agent needs the user to confirm or provide information before the document is complete.
- `guidance` — instruction for what to do with this section (send via certified mail, notarize before filing, etc.)

Comments are written to `document_comments` table. Each comment links to a `section_ref` so the frontend can anchor it to the correct part of the document.

### 3. Document generation agent
`backend/agents/document_agent.py`

Called by template engine for comment generation. Also handles:
- Detecting whether landlord name needs SOS correction and generating the change comment
- Evaluating whether claim amount exceeds jurisdiction limit and generating the decision comment
- Verifying all exhibit references in evidence cover sheet
- Generating the default judgment hardgate check — blocks generation if response deadline has not passed

### 4. PDF export
`backend/documents/pdf_export.py`

Uses WeasyPrint to render the assembled HTML document to PDF. Called only when all comments are resolved and user clicks Export.

- Applies a clean legal document CSS stylesheet
- Includes case header, page numbers, signature line
- Saves PDF to `exports/` container in Azure Blob Storage
- Updates `documents` record: status → `exported`, `exported_at` timestamp
- Returns a time-limited signed URL for the frontend download link

### 5. Document versioning
When a document is re-generated (e.g. user updates information and regenerates the demand letter):
- New `documents` record is created with `version = previous + 1`
- `parent_doc_id` links to the previous version
- Previous version is preserved — never overwritten
- Frontend shows version history with timestamps

### 6. Document generation endpoints
```
POST /cases/{case_id}/documents/generate
Body: { "document_type": "demand_letter" }
Returns: { "document_id": uuid, "comment_count": int, "preflight_issues": [] }

GET  /cases/{case_id}/documents
Returns: all documents for this case with status and version

GET  /cases/{case_id}/documents/{document_id}
Returns: document HTML, field map, all comments

PUT  /cases/{case_id}/documents/{document_id}/comments/{comment_id}
Body: { "resolved": true, "resolution_text": "confirmed" }
Resolves a single comment

POST /cases/{case_id}/documents/{document_id}/export
Triggers PDF generation — only succeeds if all comments resolved
Returns: signed download URL
```

### 7. Document studio — frontend
Refer to the UI mockup for the three-column layout and design language.

**Left column — document list**
- All documents for this case, ordered by workflow step
- Status indicator per document: draft / comments pending / ready / exported / filed / locked
- Locked documents shown at reduced opacity with lock icon
- Plus button triggers generate dialog

**Generate dialog**
When user clicks Generate or the plus button:
- Show list of generatable documents for current case stage
- Highlight which documents are locked and why
- On selection, call generate endpoint
- Show preflight issues if any — tell user exactly what is missing

**Center column — document viewer**
- Renders document HTML with inline highlights
- Three highlight colors:
  - Amber underline → `changed` comment (agent modified wording)
  - Teal underline → `clarification` comment (needs user input)
  - Red underline → `guidance` comment (instruction)
- Clicking a highlight scrolls the corresponding comment into view in right column
- Version selector at top if multiple versions exist

**Right column — comments panel**
- All unresolved comments listed in order
- Each comment card shows: type badge, explanation text, Accept / Edit / Confirm buttons
- Clicking a comment card highlights the corresponding section in the center document viewer
- Running count of unresolved comments shown at top
- Export button activates only when count reaches zero

**Export behavior**
- Export button calls export endpoint
- On success, opens a file download dialog for the PDF
- Updates document status to `exported` in UI
- Prompts user to log any associated expenses (e.g. certified mail cost) — links to expense tracker

### 8. Document templates — full definitions
All six YAML template definitions must be built in `backend/documents/templates/`. Full field maps, preflight rules, state variations, and validation rules for each:

```
demand_letter.yaml
small_claims_petition.yaml
amended_petition.yaml
motion_to_amend.yaml
motion_default_judgment.yaml
evidence_cover_sheet.yaml
```

The complete field map for each document is defined in `phase-05-templates.md`.

### 9. Expense prompt on document export
After any document export, check if the document type has associated typical expenses:
- `demand_letter` → prompt: did you send this via certified mail? Log the cost.
- `small_claims_petition` → prompt: did you pay the filing fee? Log the amount.
- `motion_default_judgment` → prompt: did you pay for constable service? Log the amount.

This ensures recoverable expenses are captured without the user having to remember.

## Definition of done
- [ ] Demand letter generates correctly for a Texas test case
- [ ] All required fields are populated from case data
- [ ] SOS name correction comment is generated and displayed correctly
- [ ] Jurisdiction limit check correctly flags claims over $20,000
- [ ] All comments resolve correctly and export button activates at zero
- [ ] PDF renders cleanly and downloads successfully
- [ ] Document is stored in Azure Blob and record updated in database
- [ ] Versioning works — re-generating creates version 2 and preserves version 1
- [ ] Small claims petition generates correctly with demand letter as prerequisite
- [ ] Amended petition always generates with motion to amend as a package
- [ ] Default judgment hard gate blocks generation before response deadline
- [ ] Evidence cover sheet auto-populates from evidence table
- [ ] Expense prompt appears after demand letter and petition exports

## What is NOT in this phase
- Timeline UI and deadline tracking (Phase 6)
- SMS notifications on document ready (Phase 6)
- Court tracking (Phase 7)
