# Phase 3 — Intake UI, conversational agent, and tool calling

## Goal
Build the full new case flow. A user fills out the structured intake form, the agent fires tool calls in the background to research their situation, and a chat interface opens for clarifying questions. By the end of this phase a user can open a case, have the agent verify their landlord, load state law, and reach a research-complete state.

## What to build

### 1. Case creation endpoint
```
POST /cases
```
- Creates a record in `cases` table with status `intake`
- Creates a record in `case_details_security_deposit`
- Spins up a dedicated Foundry IQ knowledge base for this case via `uploader.create_case_knowledge_base(case_id)`
- Stores `foundry_kb_id` on the case record
- Returns `case_id` to frontend

### 2. Intake form — frontend (5 steps)

Each step is a distinct UI section. Navigation between steps is controlled — the user cannot skip forward. Refer to the UI mockup for component placement and design.

**Step 1 — Who you are**
Fields: full legal name, current address, email, phone number.

**Step 2 — The property**
Fields: property address, state (dropdown), county (auto-populates from state), landlord type (radio — individual / management company / not sure), landlord name as on lease (with info pip), landlord mailing address.

Lease upload zone at the bottom of Step 2. Clearly marked optional. If uploaded, triggers lease parser immediately in background — does not block step progression.

Assistant button below the upload zone.

**Step 3 — The deposit**
Fields: deposit amount, move-in date, move-out date, keys returned date, amount returned (if any), date returned, forwarding address, forwarding address proof (yes/no with upload option), communication received (radio — none / itemized list / partial explanation / verbal only).

**Step 4 — Evidence**
Upload zone for: move-in inspection report, move-out inspection report, move-in photos, move-out photos, all written communications with landlord, proof of forwarding address, proof of deposit payment. Each item labeled required / strongly recommended / if applicable.

**Step 5 — Review**
Summary of everything entered. Edit links back to each section. Submit button triggers the research agent.

### 3. Research progress UI
After Step 5 submit, user sees the research progress panel. A live list of tool calls being made with status indicators — pending, running, complete. Uses WebSocket to stream updates from the backend in real time.

Items shown:
- Verifying landlord entity via Secretary of State
- Loading [STATE] security deposit law
- Calculating deadline and days overdue
- Checking county court filing procedures
- Parsing lease (if uploaded)
- Running case assessment

### 4. Intake agent (backend)
`backend/agents/intake_agent.py`

Orchestrates all tool calls after form submission. Runs asynchronously. Updates `agent_sessions` table throughout. Pushes WebSocket events to the frontend for each tool call result.

Tool call sequence:
1. SOS lookup → verify landlord legal name and registered agent
2. Foundry IQ query → check if state law is loaded
3. If state not loaded → trigger on-demand ingest, wait for completion
4. Foundry IQ query → load state law for this case
5. Deadline calculator → compute deadline date, days overdue, violation status
6. County court lookup → filing procedures, fees, correct precinct
7. Address validator → verify landlord address for service
8. Lease parser agent → if lease was uploaded (runs in parallel)
9. Write all findings to `case_details_security_deposit`
10. Update case status to `researching` → `assessment`
11. Push WebSocket event: research complete, assessment ready

### 5. Tool implementations
Build each tool in `backend/tools/`:

**`sos_lookup.py`**
- Accepts state and entity name
- Queries state Secretary of State business search portal
- Returns: verified legal name, registered agent, address, entity status
- Scrapes using httpx + BeautifulSoup for static portals
- Falls back to Playwright for JS-rendered portals
- Stores result in `case_details_security_deposit`

**`foundry_iq.py`**
- `query_knowledge_base(kb_id, query_text)` → returns grounded chunks with citations
- `add_document_to_case_kb(case_id, blob_path, doc_type)` → registers uploaded doc
- Wraps Azure AI Foundry agentic retrieval API

**`deadline_calculator.py`**
- Accepts move-out date, keys returned date, forwarding address date, state return deadline days
- Returns: deadline date, days overdue, violation confirmed boolean
- Pure Python date logic — no external API

**`court_lookup.py`**
- Queries `kb-court-procedures` Foundry IQ knowledge base
- Returns: correct court name, address, precinct (if applicable), filing fee, online filing URL

**`address_validator.py`**
- Calls USPS Web Tools Address Verification API
- Returns: standardized address, deliverability status
- Flags PO boxes for agent comment in document generation

### 6. WebSocket endpoint
`backend/api/routes/chat.py`

```
WS /ws/cases/{case_id}
```
- Authenticates via JWT passed as query param on connect
- Receives agent progress events and pushes to connected client
- Also handles chat messages in both directions
- Keeps conversation history in `conversation_messages` table

### 7. Chat interface — frontend
Opens after research phase completes. Refer to mockup for placement — chat sits in the right panel of the timeline screen.

- Displays all messages from `conversation_messages` for this case
- User can type questions at any time after research completes
- Agent responses stream token by token via WebSocket
- Dynamic forms: if agent sends `message_type: dynamic_form`, render the `form_schema` as an inline form inside the chat panel. On submit, send `form_response` back.

### 8. Lease parser agent
`backend/agents/lease_parser_agent.py`

Triggered when a lease document is uploaded — either during intake or later from the Documents screen.

- Extracts text from PDF using `pdfplumber` or from DOCX using `python-docx`
- Passes extracted text to LLM with a constrained extraction prompt
- Extracts: party names, dates, deposit amount, notice requirements, pet policy, early termination clause, maintenance responsibilities
- Identifies and flags clauses that may be unenforceable in the user's state
- Writes structured results to `lease_parse_results` table
- Writes summary to case Foundry IQ knowledge base
- Updates `case_details_security_deposit.lease_required_notice_days`
- Returns structured output to frontend for display

### 9. Per-case Foundry IQ knowledge base population
After each tool call completes, write findings to the case KB:
- Verified landlord information
- State law summary for this case
- Lease parse results
- All uploaded documents (registered as knowledge sources)

This is the grounding layer for all subsequent agent calls — document generation, assessment, chat.

## Definition of done
- [ ] User completes all 5 intake steps without errors
- [ ] Lease upload triggers parser and results appear in UI
- [ ] Research phase runs all tool calls and streams progress to frontend
- [ ] SOS lookup returns verified landlord name for a Texas management company test case
- [ ] State law loads from Foundry IQ for Texas
- [ ] Deadline calculation is correct for a test case with known dates
- [ ] Case status updates correctly through intake → researching → assessment
- [ ] WebSocket connection stable — no dropped events in testing
- [ ] Chat panel accepts user messages and agent responds correctly
- [ ] All findings written to database and case Foundry IQ KB

## What is NOT in this phase
- Case assessment UI and logic (Phase 4)
- Document generation (Phase 5)
- Timeline UI (Phase 6)
- SMS notifications (Phase 6)
