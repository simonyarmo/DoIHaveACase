# Phase 2 — Foundry IQ knowledge bases and ingestion pipeline

## Goal
Build and seed the knowledge layer that all agents depend on. By the end of this phase, Foundry IQ has verified Texas security deposit law loaded, court procedures for Travis and Harris counties loaded, all document templates registered, and the ingestion pipeline running. All agent queries in later phases read from this layer — nothing is hardcoded.

## What to build

### 1. Foundry IQ knowledge base setup
Create the following knowledge bases in the Azure AI Foundry portal and register their IDs in environment variables:

```
kb-state-law-security-deposit     → state law files per state
kb-court-procedures                → filing procedures per county
kb-document-templates              → legal document template definitions
```

Per-case knowledge bases are created dynamically at runtime (Phase 3) — not here.

### 2. State law markdown files
Create the following files in `backend/knowledge/state_law/`:

```
TX.md    → full Texas schema (reference implementation — see phase-02-tx-law.md)
CA.md    → California schema
FL.md    → Florida schema
```

Every file must follow the exact schema defined in `phase-02-law-schema.md`. Do not deviate from the schema structure — agent queries depend on consistent field locations.

Seed only TX.md completely for the hackathon. CA.md and FL.md can have placeholder structures with a `status: stub` flag in the header.

### 3. Ingestion pipeline
Build the full pipeline in `backend/knowledge/ingestion/`:

```
pipeline.py      → orchestrator (seed / refresh / on-demand modes)
fetcher.py       → pulls from official state legislature websites
parser.py        → LLM-assisted extraction into schema
validator.py     → completeness check and diff against existing
uploader.py      → pushes markdown to Blob Storage, registers in Foundry IQ
freshness.py     → tracks age of each state file, flags for refresh
sources/
  registry.py          → maps state to source URLs
  state_sources.yaml   → authoritative source list per state
```

Full implementation detail in `phase-02-pipeline.md`.

### 4. Source registry
Populate `state_sources.yaml` with official sources for TX, CA, FL to start. Every source must be a government or official court URL — no third-party legal sites.

### 5. Document template registration
Upload all six document template YAML files to Foundry IQ `kb-document-templates`:

```
demand_letter.yaml
small_claims_petition.yaml
amended_petition.yaml
motion_to_amend.yaml
motion_default_judgment.yaml
evidence_cover_sheet.yaml
```

Full template field definitions in `phase-05-templates.md` (built in Phase 5, registered here so agents can reference them from Phase 3 onward).

### 6. Foundry IQ uploader utility
Build `backend/knowledge/ingestion/uploader.py`:
- Upload markdown file to Azure Blob Storage
- Register as a Foundry IQ knowledge source via API
- Attach knowledge source to the correct knowledge base
- Return the `foundry_source_id` for storage in `law_freshness` table
- Separate method: `create_case_knowledge_base(case_id)` — called at case creation

### 7. Celery scheduled task
Create `backend/tasks/law_refresh.py`:
- `refresh_all_states` task runs every Sunday at 2am
- Iterates all states in `law_freshness` table where `next_review <= now()`
- Calls pipeline in REFRESH mode for each
- Any state flagged `pending_review = true` sends admin notification instead of auto-publishing

### 8. On-demand ingest API endpoint
```
POST /knowledge/ingest/{state}
```
- Called when a user selects a state not yet in Foundry IQ
- Triggers `on_demand_ingest` Celery task immediately
- Returns `{status: "ingesting", estimated_seconds: 120}`
- Frontend polls `GET /knowledge/status/{state}` until complete
- Case research proceeds only after status returns `ready`

### 9. Human review flag
Any state file flagged `needs_review = true` by the validator:
- Sets `law_freshness.pending_review = true`
- Does NOT publish to Foundry IQ
- Writes flagged content to `knowledge-sources/pending-review/{state}.md` in Blob Storage
- Sends admin SMS via Twilio (reuse notification service from Phase 6 — stub it here)

## Definition of done
- [ ] Three Foundry IQ knowledge bases created and reachable via API
- [ ] TX.md fully populated and verified against official Texas statute
- [ ] TX.md uploaded to Blob Storage and indexed in `kb-state-law-security-deposit`
- [ ] CA.md and FL.md exist as stubs — pipeline can expand them later
- [ ] `law_freshness` table has records for TX, CA, FL with correct source URLs
- [ ] Ingestion pipeline runs end-to-end for TX in seed mode without error
- [ ] Celery scheduled task is registered (does not need to run — just registered)
- [ ] On-demand ingest endpoint returns correct status
- [ ] Document template YAMLs are uploaded to `kb-document-templates`

## What is NOT in this phase
- No agents querying the knowledge bases yet (Phase 3+)
- No per-case knowledge bases (Phase 3)
- No user-facing UI for this (all backend)
- CA and FL do not need to be fully populated
