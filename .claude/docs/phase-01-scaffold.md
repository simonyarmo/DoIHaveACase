# Phase 1 — Project scaffold, database, auth, and Azure setup

## Goal
Stand up the full project structure with a working backend, connected database, authentication, and Azure services provisioned. By the end of this phase you can create a user account, log in, and have all infrastructure ready for agents and knowledge bases.

## What to build

### 1. Repository structure
Initialize the monorepo with the following layout:

```
depositshield/
├── backend/
│   ├── main.py
│   ├── config.py
│   ├── api/
│   │   ├── routes/
│   │   └── dependencies.py
│   ├── agents/
│   ├── tools/
│   ├── documents/
│   │   └── templates/
│   ├── knowledge/
│   │   ├── state_law/
│   │   └── ingestion/
│   ├── models/
│   ├── schemas/
│   ├── services/
│   ├── tasks/
│   └── tests/
├── frontend/
│   ├── src/
│   │   ├── pages/
│   │   ├── components/
│   │   └── store/
│   └── public/
└── docs/
    └── phases/
```

### 2. Backend setup
- Initialize FastAPI app in `main.py`
- Configure CORS, exception handlers, and lifespan events
- Set up Pydantic settings in `config.py` pulling from environment variables
- Install all dependencies — see `phase-01-dependencies.md`

### 3. Database
- Create Supabase project
- Run all migrations via Alembic — see `phase-01-schema.md` for full table definitions
- Set up SQLAlchemy async engine
- Configure row-level security policies on Supabase
- Seed the `law_freshness` table with placeholder records for TX, CA, FL as the first three states

### 4. Authentication
- Enable Supabase Auth (email + password)
- Wire Supabase JWT verification into FastAPI via `dependencies.py`
- Protect all routes except `/health` and `/auth/*`
- Store user record in local `users` table on first login

### 5. Azure services
Provision the following in Azure portal:
- Azure AI Foundry project
- Azure AI Search resource (free tier for dev)
- Azure Blob Storage account with three containers: `case-documents`, `knowledge-sources`, `exports`
- Azure OpenAI connection inside Foundry project (use `gpt-4o` as the default model)

Verify all connection strings and keys are reachable from the backend via environment variables.

### 6. Redis
- Provision Upstash Redis instance
- Wire as Celery broker in `tasks/celery_app.py`
- Confirm Celery worker starts cleanly

### 7. Frontend setup
- Initialize Vite + React project
- Install Tailwind CSS, shadcn/ui, Zustand, React Query, React Hook Form
- Set up base routing (React Router)
- Create placeholder pages for all five screens
- Connect Supabase auth client — login and signup pages working by end of phase

### 8. Environment configuration
Create `.env.example` with all required variables documented. See `phase-01-dependencies.md` for the full list.

### 9. Health check endpoint
`GET /health` returns service status for backend, database, Redis, and Azure connectivity. Used to verify the full stack is wired before moving to Phase 2.

## Definition of done
- [ ] User can sign up and log in via the frontend
- [ ] JWT is passed to backend and verified on protected routes
- [ ] Database tables exist and accept writes
- [ ] Azure Blob Storage containers are created and accessible from backend
- [ ] Azure AI Foundry project is provisioned and reachable
- [ ] Celery worker starts and processes a test task
- [ ] `/health` endpoint returns green for all services
- [ ] Frontend loads with placeholder navigation between all screens

## What is NOT in this phase
- No agents or Foundry IQ knowledge bases yet
- No real case data or forms
- No document generation
- No SMS
