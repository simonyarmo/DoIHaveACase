# Phase 8 — Frontend polish, full integration, and demo preparation

## Goal
Wire all phases together into a seamless end-to-end experience. Polish the UI to match the design mockup. Harden error handling across all flows. Prepare a clean, repeatable hackathon demo that shows the full journey from case creation to document export in under 10 minutes.

## What to build

### 1. Full end-to-end integration pass
Walk every user flow from start to finish and verify nothing breaks across phase boundaries. Known integration points to test explicitly:

- Intake completion → assessment agent triggers automatically
- Assessment complete → action plan timeline events created
- Demand letter exported → demand_sent timeline event auto-completes → petition step unlocks
- Petition exported → expense prompt appears → court case number entry appears
- Court case number entered → tracking starts → first poll runs immediately
- Hearing detected → court prep guide unlocks → deadline alerts scheduled
- All SMS alerts deliver to verified phone number at correct times

### 2. Error handling — backend
Every API endpoint and agent must return structured errors the frontend can display usefully. No raw stack traces to the client.

Standard error response format:
```json
{
  "error": true,
  "code": "SOS_LOOKUP_FAILED",
  "message": "We could not verify the landlord entity with the Texas Secretary of State. You can continue and enter the legal name manually.",
  "recoverable": true,
  "fallback_action": "manual_entry"
}
```

Error codes to implement:
- `SOS_LOOKUP_FAILED` — portal unreachable or entity not found, allow manual entry
- `STATE_LAW_NOT_LOADED` — on-demand ingest triggered, show progress
- `FOUNDRY_QUERY_FAILED` — retry once, then surface error with support contact
- `DOCUMENT_PREFLIGHT_FAILED` — return list of missing fields
- `EXPORT_COMMENTS_UNRESOLVED` — return count of unresolved comments
- `COURT_PORTAL_UNREACHABLE` — show fallback message with manual link
- `SMS_SEND_FAILED` — log error, do not surface to user (silent fail with retry)

### 3. Error handling — frontend
Every API call is wrapped in error boundaries. Users never see a blank screen or raw error text.

- Network errors → retry button with explanation
- Auth expiry → redirect to login with "session expired" message
- Not found → friendly 404 within the app shell
- Agent timeout → "still working" message with estimated wait time
- Form validation → inline field-level errors, not page-level alerts

### 4. Loading states
Every async operation has a loading state. Nothing appears to hang.

- Intake form submission → research progress panel with live tool call list
- Agent running → spinner with "thinking" label in chat
- Document generating → skeleton loader in document viewer
- PDF exporting → progress indicator on export button
- Court polling → "checking court records..." status in tracking card

### 5. Empty states
Every screen that can be empty has a designed empty state — not a blank page.

- Dashboard with no cases → "Start your first case" call to action
- Documents screen with no documents → explains what documents are and how to generate the first one
- Timeline with no events → shows expected first step
- Evidence section with no uploads → upload prompt with guidance

### 6. Dashboard final wiring
Connect all four stat cells to live data:

- Active cases → count of cases where status not in (resolved, closed_no_case)
- Case expenses → sum of recoverable expenses across all active cases
- Documents → count of documents with status exported
- Next deadline → days to earliest incomplete deadline event across all cases

Alert bar appears dynamically when any deadline is within 7 days.

### 7. Navigation and routing
React Router routes:

```
/                     → redirect to /dashboard
/dashboard            → Dashboard screen
/cases/new            → New case intake (step 1)
/cases/new/step/:n    → New case intake (step n)
/cases/:id            → Case timeline (default case view)
/cases/:id/assessment → Assessment screen
/cases/:id/documents  → Document studio
/settings/notifications → Notification settings
/auth/login           → Login
/auth/signup          → Sign up
```

Route guards: all /cases/* and /dashboard routes require authenticated session. Unauthenticated users redirect to /auth/login with return URL preserved.

### 8. React Query caching strategy
Define cache keys and invalidation rules for all major data types:

```javascript
QUERY_KEYS = {
  cases:       ['cases'],
  case:        (id) => ['cases', id],
  timeline:    (id) => ['cases', id, 'timeline'],
  assessment:  (id) => ['cases', id, 'assessment'],
  documents:   (id) => ['cases', id, 'documents'],
  document:    (caseId, docId) => ['cases', caseId, 'documents', docId],
  expenses:    (id) => ['cases', id, 'expenses'],
  tracking:    (id) => ['cases', id, 'tracking'],
  messages:    (id) => ['cases', id, 'messages'],
}

INVALIDATIONS = {
  // When a case status changes, invalidate case, timeline, and dashboard
  case_status_change: ['cases', 'cases/:id', 'cases/:id/timeline'],
  // When a document is exported, invalidate documents and expenses (prompt)
  document_exported: ['cases/:id/documents', 'cases/:id/expenses'],
  // When a timeline event completes, invalidate timeline and case
  event_complete: ['cases/:id/timeline', 'cases/:id'],
}
```

### 9. WebSocket connection management
The WebSocket connection to `/ws/cases/{case_id}` must handle:
- Automatic reconnect on disconnect (exponential backoff, max 5 retries)
- JWT refresh if token expires mid-session
- Graceful degradation if WebSocket unavailable — fall back to 5-second polling on `/cases/{case_id}/messages`
- Connection status indicator in the chat header (online dot)

### 10. Mobile responsiveness
The app is primarily desktop but must not break on smaller screens. Minimum supported width: 768px (tablet).

Breakpoint behavior:
- Below 900px: sidebar collapses to icon-only rail (tooltips on hover)
- Below 768px: show a "best viewed on desktop" banner — do not attempt to fully reflow the three-column layouts

### 11. Hackathon demo script
Prepare a clean demo case pre-seeded in the database that can be used for live demonstration. The demo case should be at the "demand sent, response deadline approaching" state — the most visually compelling moment in the product.

Demo flow (target: 8 minutes):
1. Show dashboard — two cases, deadline alert bar, expense total (1 min)
2. Open new case intake — walk through steps 2 and 3, show SOS lookup running live (2 min)
3. Show research progress panel — tool calls firing in real time (1 min)
4. Open assessment screen — walk through findings, strength bars, recovery range (1 min)
5. Open document studio — show demand letter with inline comments, resolve one comment live (2 min)
6. Show notifications settings — trigger test SMS live on demo phone (1 min)

Prepare a backup demo video in case of live environment failure.

### 12. Deployment — hackathon
```
Frontend:  Vercel (deploy from GitHub main branch)
Backend:   Railway (Python service, env vars configured)
Database:  Supabase (existing dev instance)
Redis:     Upstash (existing dev instance)
Azure:     Azure AI Foundry + Search + Blob (existing dev resources)
```

Pre-deployment checklist:
- [ ] All environment variables set in Railway and Vercel
- [ ] Database migrations run on production Supabase
- [ ] TX.md ingested into production Foundry IQ knowledge base
- [ ] Demo case seeded in production database
- [ ] Test SMS sends from production Twilio number to demo phone
- [ ] All six document templates generate correctly on production
- [ ] WebSocket connection stable under production Railway URL
- [ ] Health check endpoint returns green for all services

## Definition of done
- [ ] Full end-to-end flow works without manual intervention for a Texas security deposit case
- [ ] All error states display correctly and no raw errors reach the user
- [ ] All loading states render correctly — no blank intermediate states
- [ ] All empty states have designed UI
- [ ] Dashboard stat cells are live from real data
- [ ] All React Router routes work including auth guards
- [ ] WebSocket reconnects automatically after simulated disconnect
- [ ] App layout holds at 768px width
- [ ] Demo case is seeded and demo script runs cleanly in under 10 minutes
- [ ] Production deployment passes full pre-deployment checklist
- [ ] Backup demo video recorded and accessible

## Post-hackathon extension path
When extending the product after the hackathon, the natural build order is:

1. Add habitability dispute type — new intake branch, new law KB entries, same document studio
2. Add lease violation dispute type — same pattern
3. Expand court tracking to more counties — new adapter per county, no core changes
4. Expand state law coverage — run ingestion pipeline for additional states
5. Add attorney review marketplace — attorneys can be invited to review flagged documents
6. Add mediation tracking — log mediation sessions and outcomes
7. Add multi-case dashboard analytics — win rates, average recovery, time to resolution
