# Session 01 — Phase 1 Scaffold + Security Fixes + Workflow Setup

## What was built

**Phase 1 scaffold (full monorepo from scratch)**
- FastAPI async backend with SQLAlchemy 2.0, Alembic, asyncpg, Pydantic Settings
- 15 Alembic migrations (all 15 database tables chained 001→015)
- RLS policies for all case-linked tables (run against Supabase after migrations)
- SQLAlchemy ORM models for all 15 tables
- Supabase JWT auth + local user auto-provisioning
- Celery + Upstash Redis task queue skeleton
- Vite/React 18.3/TypeScript frontend with Tailwind + shadcn/ui-style components
- Supabase JS client, Zustand auth store, React Query, React Router v6
- Auth pages (Login, Signup) with React Hook Form
- ProtectedRoute + AppLayout with nav sidebar
- Placeholder screens for every Phase 2–8 route (Dashboard, CaseIntake, CaseTimeline, CaseAssessment, DocumentStudio, NotificationSettings)
- `.env.example` covering all services (Azure, Supabase, Redis, Twilio, USPS)
- `.gitignore` covering venv, node_modules, .env, editor files

**Code review (10 findings fixed)**
- Fixed JWT verification using the wrong secret — was using the public anon key; now uses `SUPABASE_JWT_SECRET` (a separate private value from Supabase dashboard → Project Settings → API → JWT Settings)
- Fixed race condition in user auto-creation — two concurrent first-logins would both insert, loser got an unhandled IntegrityError; now wrapped in `try/except IntegrityError` with rollback + re-select
- Fixed `user_metadata: null` crash — `payload.get("user_metadata", {})` returns `None` when key is explicitly null; changed to `(payload.get("user_metadata") or {})`
- Fixed `login()` not guarding `result.session is None` — unlike `signup()` which already had the guard; added matching check
- Fixed `signup()` not creating local users row — lazily deferred to first authenticated request; now calls `get_or_create_local_user()` immediately after signup
- Extracted shared `services/users.py::get_or_create_local_user()` — race-safe helper used by both signup and the auth dependency
- Added `case_parties` RLS policy — it was the only case-linked table missing `ENABLE ROW LEVEL SECURITY`
- Added RLS architecture comment — policies don't protect backend's direct Postgres connection (superuser bypasses RLS); documented that app-level filtering is the real guard
- Added `protected_router = APIRouter(dependencies=[Depends(get_current_user)])` in `main.py` — Phase 2+ feature routers must be included into this, not added directly to `app`, so auth is structural not opt-in
- Added `logger.exception(...)` to the global exception handler — was silently swallowing every unhandled error with no log trace
- Broadened JWT decode `except` to `(JWTError, ValueError, TypeError, AttributeError)` — python-jose can raise non-JWTError types for malformed/garbage tokens

**Workflow setup**
- `CLAUDE.md` created at repo root — documents the branch → PR → `/code-review` → fix → `gh pr merge` flow that every phase ships through from Phase 2 onward
- `.claude/hooks/guard-main-push.py` — PreToolUse hook that blocks any direct `git push` to `main`/`master`; tested against 13 cases (chained commands, force-push, colon refspecs, word-boundary edge cases, false-positive strings)
- `.claude/settings.json` — wires the hook into Claude Code's PreToolUse pipeline
- `gh` CLI installed via Homebrew, authenticated as `simonyarmo`
- Phase 1 committed to `main` (99 files, root commit `6483bce`) and pushed to `origin`

---

## What's next

**Before writing any code — provision the services:**
- [ ] Create Supabase project → grab `SUPABASE_URL`, `SUPABASE_ANON_KEY`, `SUPABASE_SERVICE_KEY`, `SUPABASE_JWT_SECRET`, `DATABASE_URL`
- [ ] Run `alembic upgrade head` against the Supabase database to apply all 15 migrations
- [ ] Run `backend/migrations/rls_policies.sql` against the Supabase SQL editor
- [ ] Create Upstash Redis instance → fill in `UPSTASH_REDIS_URL`, `UPSTASH_REDIS_TOKEN`, `CELERY_BROKER_URL`, `CELERY_RESULT_BACKEND`
- [ ] Create Azure AI Foundry project + OpenAI deployment + AI Search index + Blob Storage account (needed for Phase 3+, not blocking Phase 2)
- [ ] Add a Twilio number (needed for Phase 6+)
- [ ] Copy `.env.example` to `backend/.env` and `frontend/.env` and fill in real values
- [ ] Generate a random `SECRET_KEY` (`openssl rand -hex 32`)

**Phase 2 — Law knowledge base** (spec: `.claude/docs/phase-02-knowledge.md`, `.claude/docs/phase-02-law-schema.md`)
- This is the next phase to build when services are provisioned and `.env` is populated
- Per the workflow in `CLAUDE.md`: work on a `phase-02-knowledge` branch, then PR → `/code-review` → merge
