# Phase 1 — Dependencies and environment configuration

## Backend dependencies (requirements.txt)

```
# Core
fastapi==0.111.0
uvicorn[standard]==0.29.0
pydantic==2.7.0
pydantic-settings==2.2.1
python-dotenv==1.0.1

# Database
sqlalchemy[asyncio]==2.0.30
alembic==1.13.1
asyncpg==0.29.0
supabase==2.4.6

# Auth
python-jose[cryptography]==3.3.0
passlib[bcrypt]==1.7.4

# Task queue
celery==5.4.0
redis==5.0.4

# Azure
azure-ai-projects==1.0.0b3
azure-identity==1.16.0
azure-search-documents==11.6.0b4
azure-storage-blob==12.20.0

# HTTP
httpx==0.27.0

# Utilities
python-multipart==0.0.9
```

## Frontend dependencies (package.json)

```json
{
  "dependencies": {
    "react": "^18.3.0",
    "react-dom": "^18.3.0",
    "react-router-dom": "^6.23.0",
    "@tanstack/react-query": "^5.40.0",
    "zustand": "^4.5.2",
    "react-hook-form": "^7.51.5",
    "@supabase/supabase-js": "^2.43.4",
    "lucide-react": "^0.383.0"
  },
  "devDependencies": {
    "vite": "^5.2.11",
    "@vitejs/plugin-react": "^4.3.0",
    "tailwindcss": "^3.4.4",
    "autoprefixer": "^10.4.19",
    "postcss": "^8.4.38"
  }
}
```

## Environment variables (.env.example)

```bash
# ── Azure AI Foundry ──────────────────────────────────────
AZURE_FOUNDRY_ENDPOINT=https://your-project.api.azureml.ms
AZURE_FOUNDRY_API_KEY=your-key
AZURE_OPENAI_ENDPOINT=https://your-openai.openai.azure.com
AZURE_OPENAI_KEY=your-key
AZURE_OPENAI_DEPLOYMENT=gpt-4o

# ── Azure AI Search ───────────────────────────────────────
AZURE_SEARCH_ENDPOINT=https://your-search.search.windows.net
AZURE_SEARCH_API_KEY=your-key

# ── Azure Blob Storage ────────────────────────────────────
AZURE_BLOB_CONNECTION_STRING=DefaultEndpointsProtocol=https;...
AZURE_BLOB_ACCOUNT_NAME=your-account
AZURE_BLOB_ACCOUNT_KEY=your-key

# ── Supabase ──────────────────────────────────────────────
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_ANON_KEY=your-anon-key
SUPABASE_SERVICE_KEY=your-service-key
DATABASE_URL=postgresql+asyncpg://postgres:password@db.your-project.supabase.co:5432/postgres

# ── Redis (Upstash) ───────────────────────────────────────
UPSTASH_REDIS_URL=rediss://your-redis.upstash.io:6379
UPSTASH_REDIS_TOKEN=your-token
CELERY_BROKER_URL=rediss://:your-token@your-redis.upstash.io:6379/0
CELERY_RESULT_BACKEND=rediss://:your-token@your-redis.upstash.io:6379/1

# ── External APIs ─────────────────────────────────────────
USPS_API_KEY=your-key
TWILIO_ACCOUNT_SID=your-sid
TWILIO_AUTH_TOKEN=your-token
TWILIO_PHONE_NUMBER=+15125550100

# ── App ───────────────────────────────────────────────────
SECRET_KEY=your-secret-key-min-32-chars
ENVIRONMENT=development
FRONTEND_URL=http://localhost:5173
```

## Azure provisioning steps

### 1. Azure AI Foundry
```
Portal → Create resource → Azure AI Foundry
  Project name: depositshield-dev
  Region: East US 2 (lowest latency for OpenAI)
  
Inside project:
  → Connections → Add → Azure OpenAI
  → Select model: gpt-4o
```

### 2. Azure AI Search
```
Portal → Create resource → Azure AI Search
  Name: depositshield-search
  Tier: Free (for dev), Basic (for prod)
  Region: same as Foundry project
```

### 3. Azure Blob Storage
```
Portal → Create resource → Storage account
  Name: depositshieldstore
  Redundancy: LRS (dev), GRS (prod)

Create containers:
  case-documents    → private access
  knowledge-sources → private access
  exports           → private access
```

## Supabase row-level security policies

Run these after Alembic migrations:

```sql
-- Users can only read their own data
ALTER TABLE users ENABLE ROW LEVEL SECURITY;
CREATE POLICY "users_own_data" ON users
  FOR ALL USING (auth.uid()::text = id::text);

-- Users can only access their own cases
ALTER TABLE cases ENABLE ROW LEVEL SECURITY;
CREATE POLICY "cases_own_data" ON cases
  FOR ALL USING (
    user_id IN (
      SELECT id FROM users WHERE auth.uid()::text = id::text
    )
  );

-- Apply same pattern to all case-linked tables
-- case_details_security_deposit
-- documents
-- evidence
-- timeline_events
-- case_expenses
-- conversation_messages
-- agent_sessions
```
