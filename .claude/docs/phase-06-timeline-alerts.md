# Phase 6 — Timeline, alerts, SMS notifications, and expense tracker

## Goal
Build the case timeline UI, the deadline alert system, and SMS notifications via Twilio. By the end of this phase a user sees their full case timeline, receives text alerts for approaching deadlines and document activity, and can log and track case expenses.

## What to build

### 1. Timeline screen — frontend
Refer to the UI mockup for component placement and design language.

The timeline is driven entirely by `timeline_events` records created by the assessment agent in Phase 4. The frontend fetches and renders them — it does not compute timeline logic itself.

**Timeline entry states:**
- Done (teal icon) — `completed: true`
- Active / in progress (amber icon) — `is_deadline: true` and `completed: false` and `event_date` is approaching
- Urgent (red date text) — deadline within 7 days
- Locked (gray icon) — not yet unlocked by prior step completion
- Alert (red icon) — deadline passed without completion

**Entry rendering:**
Each entry shows: title, date or "unlocks after [prior step]", description, and an action button where applicable. Action buttons link to the relevant document in the document studio or provide direct instructions.

Locked entries render at reduced opacity. Action buttons on locked entries are disabled with a tooltip explaining what must happen first.

**Step unlock logic:**
The frontend checks `timeline_events` order and enables action buttons only when all prior required events are marked complete. The backend enforces this on document generation preflight — the frontend unlock is a UI convenience only, not a security boundary.

**Marking steps complete:**
```
PUT /cases/{case_id}/timeline/{event_id}/complete
Body: { "completed": true, "notes": "optional" }
```
Some events auto-complete from other actions (e.g. demand letter exported → demand_sent event auto-completes). Others require manual user confirmation (e.g. "I mailed the letter today").

### 2. Timeline API endpoints
```
GET  /cases/{case_id}/timeline
Returns all timeline events ordered by event_date, then by creation order

PUT  /cases/{case_id}/timeline/{event_id}/complete
Marks event complete, triggers next step unlock evaluation

POST /cases/{case_id}/timeline/events
Creates a new manual timeline event (e.g. user received a phone call)
```

### 3. Auto-complete triggers
Wire these event completions to fire automatically from other actions:

| Trigger | Auto-completes event |
|---------|---------------------|
| Demand letter exported | `demand_letter_ready` event |
| User logs certified mail tracking number | `demand_sent` event |
| Response deadline date passes with no response recorded | Unlocks petition step |
| Petition exported | `petition_ready` event |
| User marks defendant served | `service_complete` event |
| Court tracking detects hearing date | Creates `hearing_scheduled` event |

### 4. Dashboard timeline widget
The dashboard shows:
- Next action item pinned at the top (next incomplete, unlocked step)
- Deadline countdown for the most urgent approaching deadline
- Case expense running total in the stat cell (replaces "total at stake")

Stat cells on dashboard:
- Active cases (count)
- Case expenses (sum of all `recoverable: true` expenses across all cases)
- Documents (count of exported documents)
- Next deadline (days remaining to most urgent deadline)

### 5. Deadline alert Celery task
`backend/tasks/deadline_alerts.py`

Runs every day at 8am via Celery beat schedule.

```python
# Logic per case per open deadline event:
for case in all_active_cases:
    for event in case.timeline_events where is_deadline=true and completed=false:
        days_remaining = (event.event_date - today).days
        if days_remaining in [7, 3, 1, 0]:
            if not alert_already_sent_today(event):
                send_deadline_sms(user, case, event, days_remaining)
                log_to_notifications_table()
                mark_deadline_alert_sent(event)
```

Day 0 alert (deadline day) uses more urgent language — "Today is the deadline for..."

### 6. Notification service
`backend/services/notifications.py`

Full Twilio SMS integration. All message text is defined as templates in this file — nothing is free-generated.

**Message templates:**

```python
TEMPLATES = {
    "deadline_approaching": (
        "DepositShield: '{title}' deadline in {days} day(s) — {event_date}. "
        "Log in to review your next step. Reply STOP to unsubscribe."
    ),
    "deadline_today": (
        "DepositShield: Today is the deadline for '{title}'. "
        "Log in immediately to take action. Reply STOP to unsubscribe."
    ),
    "deadline_passed": (
        "DepositShield: The deadline for '{title}' has passed. "
        "Log in to see your options. Reply STOP to unsubscribe."
    ),
    "document_ready": (
        "DepositShield: Your {document_name} is ready for review. "
        "Resolve all comments before sending. Reply STOP to unsubscribe."
    ),
    "court_update": (
        "DepositShield: New court activity on case #{case_number}. "
        "{update_summary} Log in for details. Reply STOP to unsubscribe."
    ),
    "test_alert": (
        "DepositShield: Your SMS notifications are working correctly. "
        "You will receive alerts for deadlines, court updates, and documents."
    ),
}
```

**Methods:**
- `send_sms(to_number, message, case_id)` — core send, logs to notifications table
- `send_deadline_alert(user, case, event, days_remaining)`
- `send_document_ready(user, case, document_name)`
- `send_court_update(user, case, update_summary)`
- `send_test_alert(user)`

All methods check `user.sms_notifications = true` and the relevant `notification_prefs` key before sending.

### 7. Notification settings — frontend
Refer to UI mockup for design.

**Phone number field with verify flow:**
- User enters phone number
- On save, Twilio sends a 6-digit OTP via SMS
- User enters OTP in a verification dialog
- On success, `users.phone_verified = true`
- Phone number cannot receive alerts until verified

**Toggle rows:**
- Master SMS toggle (disables all if off)
- Deadline warnings
- Court updates
- Documents ready
- Landlord responses

**Test alert button:**
- Calls `POST /notifications/test`
- Button shows loading state during the 1–2 second Twilio send
- On success: button hides, "Sent!" confirmation appears for 3 seconds, button returns
- On failure: inline error message with the reason

**Notification settings API endpoints:**
```
PUT  /users/me/notifications/preferences
Body: { "sms_notifications": bool, "deadlines": bool, ... }

POST /notifications/test
Sends test SMS to verified phone number

POST /notifications/verify/send
Sends OTP to entered phone number

POST /notifications/verify/confirm
Body: { "otp": "123456" }
Confirms OTP and marks phone_verified = true
```

### 8. Expense tracker — UI and backend

**Expense entry modal:**
Triggered by:
- Plus button in the expense summary widget
- Post-export prompt after demand letter, petition, or other fee-associated documents

Fields: description, amount, date, category dropdown (filing fee / service fee / certified mail / notary / other), receipt upload (optional), recoverable toggle.

**Expense summary widget:**
Appears in the case summary sidebar panel on the timeline screen and as a stat cell on the dashboard. Shows total recoverable expenses. Clicking opens a detailed expense list.

**Expense API endpoints:**
```
POST   /cases/{case_id}/expenses
GET    /cases/{case_id}/expenses
PUT    /cases/{case_id}/expenses/{expense_id}
DELETE /cases/{case_id}/expenses/{expense_id}
GET    /cases/{case_id}/expenses/total
Returns: { "total_recoverable": float, "total_all": float }
```

**Integration with document generation (Phase 5 connection):**
The document agent reads recoverable expense total when generating petitions and default judgment motions. The `court_costs_requested` field in those templates pulls from `GET /cases/{case_id}/expenses/total`.

## Definition of done
- [ ] Timeline screen renders all events from a test case correctly
- [ ] Done / active / locked / urgent states display correctly per mockup
- [ ] Auto-complete triggers fire correctly for demand letter export and deadline pass
- [ ] Deadline alert Celery task runs and sends SMS for a test case with a deadline 7 days out
- [ ] Twilio test alert sends and delivers to a real phone number
- [ ] Phone verification OTP flow works end to end
- [ ] All notification preference toggles save and are respected by the alert task
- [ ] Expense entry modal saves correctly to database
- [ ] Recoverable expense total appears correctly on dashboard and case sidebar
- [ ] Post-export expense prompt appears after demand letter export
- [ ] Notification history is logged in `notifications` table for every send

## What is NOT in this phase
- Court tracking and live docket polling (Phase 7)
- Court update SMS alerts are wired but court_update trigger is stubbed until Phase 7
