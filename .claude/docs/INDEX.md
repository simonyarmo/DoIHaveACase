# DepositShield — Build phases index

## Product summary
AI-powered legal guidance platform for tenants filing security deposit disputes in small claims court. Integrates Microsoft Foundry IQ as the knowledge and grounding layer for all agents. Built with Python (FastAPI) backend, React frontend, Supabase (PostgreSQL), Azure AI Foundry, and Twilio SMS.

Initial scope: Texas security deposit disputes. Built to extend to additional dispute types and states without core architecture changes.

---

## Phase documents

| Phase | File | Description |
|-------|------|-------------|
| 1 | `phase-01-scaffold.md` | Project structure, database, auth, Azure setup |
| 1 | `phase-01-schema.md` | All 15 database migration files |
| 1 | `phase-01-dependencies.md` | All dependencies and environment variables |
| 2 | `phase-02-knowledge.md` | Foundry IQ knowledge bases and ingestion pipeline |
| 2 | `phase-02-law-schema.md` | State law markdown schema and full Texas reference file |
| 3 | `phase-03-intake.md` | Intake UI, conversational agent, tool calling |
| 4 | `phase-04-assessment.md` | Case assessment agent and law application engine |
| 5 | `phase-05-documents.md` | Document studio, template engine, inline comments |
| 6 | `phase-06-timeline-alerts.md` | Timeline UI, deadlines, SMS notifications, expenses |
| 7 | `phase-07-court-tracking.md` | Court portal polling and live case tracking |
| 8 | `phase-08-polish-demo.md` | Frontend polish, full integration, hackathon demo prep |

---

## Build sequence

```
Phase 1 → Phase 2 → Phase 3 → Phase 4 → Phase 5 → Phase 6 → Phase 7 → Phase 8
  │           │           │          │          │          │          │          │
Infra      Knowledge   Intake    Assess    Docs    Alerts   Court    Demo
& DB       & Foundry   & Agent   & Plan    & Gen   & SMS    Track    Ready
```

Each phase depends on the prior phase being complete. Do not start Phase 3 until Foundry IQ knowledge bases are seeded and reachable — agents in Phase 3 query them immediately.

---

## Hackathon demo target state

The demo should show a Texas security deposit case at the "demand sent, response deadline approaching in 3 days" state. This is the most compelling moment — the alert bar is visible, the petition is one step away from unlocking, the document studio has a fully commented demand letter, and a live SMS test can be triggered.

Demo runtime target: 8 minutes. Full script in `phase-08-polish-demo.md`.

---

## Extension path (post-hackathon)

The architecture supports adding new dispute types (habitability, lease violation), new states, additional court tracking adapters, and attorney review features without rebuilding core systems. See the extension path section in `phase-08-polish-demo.md` for the recommended order.

---

## Key design decisions to preserve

- Foundry IQ is load-bearing — agents never invent law, every finding cites a knowledge base source
- Every document generates from a YAML template — nothing is free-generated from scratch
- The inline comment system is the most original feature — prioritize it in the demo
- Per-case Foundry IQ knowledge bases isolate user data at the retrieval layer, not just the application layer
- The ingestion pipeline flags changes to critical legal fields for human review before going live — this is the legal safety net
- Case expenses are tracked because most states allow recovery of filing costs — surface this clearly to users
