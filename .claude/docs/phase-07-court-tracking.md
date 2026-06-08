# Phase 7 — Court tracking and live case polling

## Goal
Build the system that monitors court dockets after a case is filed and surfaces new activity to the user automatically. By the end of this phase, a user who has filed their petition can enter their case number, and the system will poll the court portal, detect new docket entries, update the timeline, and send an SMS alert — without the user ever having to call the clerk's office.

## What to build

### 1. Court case number entry — frontend
After the petition is marked as filed, a new prompt appears on the timeline screen:

```
You've filed your petition. Enter your court case number
to enable automatic case tracking.

Case number  [_______________]  [Start tracking]
```

On submit:
- Calls `POST /cases/{case_id}/tracking`
- Creates `court_tracking` record
- Kicks off an immediate first poll to verify the case number resolves on the court portal
- Confirms tracking is active with a success state

If the court portal cannot be reached or the case number is not found, show a clear error — do not silently fail.

### 2. Court tracking record management
```
POST /cases/{case_id}/tracking
Body: { "court_case_number": str, "court_name": str }
Creates tracking record, triggers immediate first poll

GET /cases/{case_id}/tracking
Returns tracking status, last checked timestamp, recent entries

DELETE /cases/{case_id}/tracking
Stops tracking for this case
```

### 3. Tracking agent
`backend/agents/tracking_agent.py`

Handles the intelligence layer on top of raw court data. When new docket entries are detected:
1. Parse the raw entry text
2. Classify the entry type (hearing scheduled / response filed / judgment entered / continuance / other)
3. Generate a plain-language summary the user can understand
4. Determine what action (if any) the user should take
5. Create a `timeline_events` record for the new entry
6. Trigger SMS alert via notification service
7. Update `court_tracking` record

**Entry classification logic:**
```python
ENTRY_PATTERNS = {
    "hearing_scheduled": ["hearing", "trial", "set for", "docket"],
    "response_filed":    ["answer", "response", "defendant filed"],
    "judgment_entered":  ["judgment", "default judgment", "order"],
    "continuance":       ["continued", "reset", "postponed"],
    "dismissal":         ["dismissed", "nonsuit"],
    "other":             []  # fallback
}
```

When a hearing is detected, the agent:
- Extracts the hearing date and time from the entry text
- Creates a `timeline_events` record with `event_type: hearing_scheduled` and `event_date` set to the hearing date
- Triggers a deadline alert chain for 7 days and 1 day before the hearing
- Unlocks the court prep guide in the action plan

### 4. Court portal scraper
`backend/tools/court_tracker.py`

Handles the mechanics of fetching docket data from court portals. Each county has a different portal structure — implement adapters per county.

**Start with:**
- Travis County, TX — `public.traviscountytx.gov` case search
- Harris County, TX — `www.hcdistrictclerk.com`

**Adapter pattern:**
```python
class CourtPortalAdapter:
    def __init__(self, county: str, state: str):
        self.adapter = self._load_adapter(county, state)

    async def fetch_docket(self, case_number: str) -> list[dict]:
        return await self.adapter.fetch(case_number)

class TravisCountyAdapter:
    async def fetch(self, case_number: str) -> list[dict]:
        # httpx GET to public portal
        # BeautifulSoup parse of docket table
        # Return list of {date, entry_text, entry_type}

class HarrisCountyAdapter:
    async def fetch(self, case_number: str) -> list[dict]:
        # Harris County uses a JS-rendered portal
        # Playwright required
        # Return same format
```

New county adapters can be added without changing the orchestration layer.

**Fallback when no adapter exists:**
If a county does not have an adapter yet, set `court_tracking.check_frequency = 0` (disabled) and display a message to the user:

```
Automatic tracking is not yet available for [COUNTY] County.
We'll notify you when it becomes available. In the meantime,
you can check your case status at [COURT_PORTAL_URL].
```

### 5. Celery polling task
`backend/tasks/court_polling.py`

```python
@shared_task
def poll_all_active_cases():
    # Runs every 6 hours via Celery beat
    # Finds all court_tracking records where check_frequency > 0
    # Checks if enough time has passed since last_checked
    # Calls poll_case for each

@shared_task
def poll_case(case_id: str):
    tracking = get_tracking_record(case_id)
    adapter = CourtPortalAdapter(tracking.court_name, case.state)
    
    new_entries = await adapter.fetch_docket(tracking.court_case_number)
    existing_entries = tracking.entries or []
    
    diff = find_new_entries(new_entries, existing_entries)
    
    if diff:
        tracking.new_entries_found = True
        tracking.entries = new_entries
        tracking.last_status = new_entries[0].entry_type
        
        for entry in diff:
            tracking_agent.process_entry(case_id, entry)
    
    tracking.last_checked = now()
    save(tracking)
```

**Celery beat schedule addition:**
```python
"poll-court-cases": {
    "task": "tasks.court_polling.poll_all_active_cases",
    "schedule": crontab(minute=0, hour="*/6")
}
```

### 6. Court prep guide
Unlocked automatically when a hearing date is detected. Stored as a static markdown file per dispute type in `backend/knowledge/court_prep/security_deposit_hearing.md`.

Content includes:
- What to bring (originals of all evidence, printed copies, lease)
- What to say in opening statement (grounded in their specific case)
- Likely questions the judge will ask
- How to present each piece of evidence
- What the defendant will likely argue and how to respond

The tracking agent personalizes the court prep guide by querying the case Foundry IQ knowledge base and inserting case-specific details (defendant name, claim amount, key dates, specific evidence they have).

Displayed as a new section on the timeline screen when unlocked.

### 7. Tracking status UI — frontend
On the timeline screen, a court tracking status card appears after case number is entered:

```
Court tracking — active
─────────────────────────────────────────
Court:        Travis County Justice Court
Case number:  2025-JC-001234
Last checked: 2 hours ago
Status:       Awaiting response

[View full docket]  [Stop tracking]
```

When new activity is detected, the card shows a highlighted alert and the new timeline entry appears in the main timeline.

### 8. Docket history view
`GET /cases/{case_id}/tracking/docket`

Returns all entries from `court_tracking.entries` as a formatted list. Displayed when user clicks "View full docket" — shows raw docket entries in chronological order with plain-language summaries alongside.

## Definition of done
- [ ] Court case number entry UI works and creates tracking record
- [ ] TravisCounty adapter fetches real docket data for a test case number
- [ ] New entry detection correctly diffs against stored entries
- [ ] Tracking agent correctly classifies hearing scheduled entry
- [ ] Hearing date extracted and timeline event created with correct date
- [ ] SMS alert fires when new entry is detected
- [ ] 7-day and 1-day hearing deadline alerts are scheduled correctly
- [ ] Court prep guide unlocks after hearing date detected
- [ ] Polling Celery task runs on schedule without errors
- [ ] Fallback message displays correctly for unsupported counties
- [ ] Docket history view shows all entries with plain-language summaries

## What is NOT in this phase
- Adapters for states other than TX (can be added post-hackathon)
- Court prep guide personalization beyond static content (can be extended)
- PACER integration for federal cases (out of scope)
