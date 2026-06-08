# Phase 1 — Database schema

All tables created via Alembic migrations in order. Run `alembic upgrade head` after each new migration file.

---

## Migration 001 — users

```sql
CREATE TABLE users (
  id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  email               VARCHAR UNIQUE NOT NULL,
  full_name           VARCHAR NOT NULL,
  phone_number        VARCHAR,
  phone_verified      BOOLEAN DEFAULT FALSE,
  sms_notifications   BOOLEAN DEFAULT TRUE,
  notification_prefs  JSONB DEFAULT '{
    "deadlines": true,
    "court_updates": true,
    "documents": true,
    "seven_day_warning": true,
    "one_day_warning": true
  }',
  subscription_tier   VARCHAR DEFAULT 'free',
  created_at          TIMESTAMP WITH TIME ZONE DEFAULT now(),
  last_active         TIMESTAMP WITH TIME ZONE
);
```

---

## Migration 002 — cases

```sql
CREATE TYPE case_status AS ENUM (
  'intake', 'researching', 'assessment', 'action_plan',
  'demand_sent', 'filed', 'hearing_scheduled', 'resolved',
  'closed_no_case'
);

CREATE TYPE dispute_type AS ENUM (
  'security_deposit',
  'habitability',
  'lease_violation'
);

CREATE TYPE resolution_type AS ENUM (
  'settled', 'won', 'lost', 'withdrawn', 'no_case'
);

CREATE TABLE cases (
  id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id           UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  status            case_status DEFAULT 'intake',
  dispute_type      dispute_type DEFAULT 'security_deposit',
  state             VARCHAR(2),
  county            VARCHAR,
  foundry_kb_id     VARCHAR,
  created_at        TIMESTAMP WITH TIME ZONE DEFAULT now(),
  updated_at        TIMESTAMP WITH TIME ZONE DEFAULT now(),
  resolved_at       TIMESTAMP WITH TIME ZONE,
  resolution_type   resolution_type
);

CREATE INDEX idx_cases_user_id ON cases(user_id);
```

---

## Migration 003 — case_details_security_deposit

```sql
CREATE TABLE case_details_security_deposit (
  id                          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  case_id                     UUID UNIQUE NOT NULL REFERENCES cases(id) ON DELETE CASCADE,

  -- Property
  property_address            VARCHAR,
  property_state              VARCHAR(2),
  property_county             VARCHAR,
  property_type               VARCHAR,

  -- Landlord
  landlord_name_as_entered    VARCHAR,
  landlord_legal_name         VARCHAR,
  landlord_sos_verified       BOOLEAN DEFAULT FALSE,
  landlord_registered_agent   VARCHAR,
  landlord_address            VARCHAR,
  landlord_sos_status         VARCHAR,
  landlord_sos_lookup_date    TIMESTAMP WITH TIME ZONE,

  -- Deposit
  deposit_amount              DECIMAL(10,2),
  amount_returned             DECIMAL(10,2) DEFAULT 0,
  date_returned               DATE,
  move_in_date                DATE,
  move_out_date               DATE,
  keys_returned_date          DATE,
  forwarding_address          VARCHAR,
  forwarding_address_proof    BOOLEAN DEFAULT FALSE,

  -- Communication
  landlord_communication      VARCHAR DEFAULT 'none',
  itemization_received        BOOLEAN DEFAULT FALSE,
  itemization_date            DATE,
  demand_letter_sent          BOOLEAN DEFAULT FALSE,
  demand_letter_date          DATE,
  demand_letter_delivery      VARCHAR,

  -- Notice
  notice_provided             BOOLEAN,
  notice_date                 DATE,
  notice_method               VARCHAR,
  notice_days                 INTEGER,
  lease_required_notice_days  INTEGER,

  -- Computed (set by agent after research)
  days_overdue                INTEGER,
  deadline_date               DATE,
  violation_confirmed         BOOLEAN,
  bad_faith_indicators        JSONB,
  estimated_recovery_min      DECIMAL(10,2),
  estimated_recovery_max      DECIMAL(10,2),
  penalty_multiplier          DECIMAL(4,1)
);
```

---

## Migration 004 — case_parties

```sql
CREATE TABLE case_parties (
  id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  case_id           UUID NOT NULL REFERENCES cases(id) ON DELETE CASCADE,
  role              VARCHAR NOT NULL,
  full_legal_name   VARCHAR NOT NULL,
  entity_type       VARCHAR,
  address           VARCHAR,
  served            BOOLEAN DEFAULT FALSE,
  served_date       DATE,
  served_method     VARCHAR,
  proof_of_service_doc_id UUID
);

CREATE INDEX idx_parties_case_id ON case_parties(case_id);
```

---

## Migration 005 — documents

```sql
CREATE TABLE documents (
  id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  case_id           UUID NOT NULL REFERENCES cases(id) ON DELETE CASCADE,
  type              VARCHAR NOT NULL,
  status            VARCHAR DEFAULT 'uploaded',
  version           INTEGER DEFAULT 1,
  parent_doc_id     UUID REFERENCES documents(id),
  storage_path      VARCHAR,
  foundry_source_id VARCHAR,
  file_name         VARCHAR,
  file_type         VARCHAR,
  file_size         INTEGER,
  uploaded_at       TIMESTAMP WITH TIME ZONE,
  generated_at      TIMESTAMP WITH TIME ZONE,
  approved_at       TIMESTAMP WITH TIME ZONE,
  exported_at       TIMESTAMP WITH TIME ZONE,
  filed_at          TIMESTAMP WITH TIME ZONE
);

CREATE INDEX idx_documents_case_id ON documents(case_id);
```

---

## Migration 006 — document_comments

```sql
CREATE TABLE document_comments (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  document_id     UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
  comment_type    VARCHAR NOT NULL,
  section_ref     VARCHAR,
  comment_text    TEXT,
  original_text   TEXT,
  new_text        TEXT,
  resolved        BOOLEAN DEFAULT FALSE,
  resolved_at     TIMESTAMP WITH TIME ZONE,
  resolution_text TEXT,
  created_at      TIMESTAMP WITH TIME ZONE DEFAULT now()
);

CREATE INDEX idx_comments_document_id ON document_comments(document_id);
```

---

## Migration 007 — evidence

```sql
CREATE TABLE evidence (
  id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  case_id           UUID NOT NULL REFERENCES cases(id) ON DELETE CASCADE,
  document_id       UUID REFERENCES documents(id),
  label             VARCHAR,
  exhibit_number    VARCHAR,
  description       TEXT,
  relevance         TEXT,
  tags              VARCHAR[],
  date_of_evidence  DATE,
  added_at          TIMESTAMP WITH TIME ZONE DEFAULT now()
);

CREATE INDEX idx_evidence_case_id ON evidence(case_id);
```

---

## Migration 008 — case_expenses

```sql
CREATE TABLE case_expenses (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  case_id         UUID NOT NULL REFERENCES cases(id) ON DELETE CASCADE,
  description     VARCHAR NOT NULL,
  amount          DECIMAL(10,2) NOT NULL,
  date            DATE NOT NULL,
  category        VARCHAR NOT NULL,
  receipt_doc_id  UUID REFERENCES documents(id),
  recoverable     BOOLEAN DEFAULT TRUE,
  created_at      TIMESTAMP WITH TIME ZONE DEFAULT now()
);

CREATE INDEX idx_expenses_case_id ON case_expenses(case_id);
```

---

## Migration 009 — lease_parse_results

```sql
CREATE TABLE lease_parse_results (
  id                          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  document_id                 UUID NOT NULL REFERENCES documents(id),
  case_id                     UUID NOT NULL REFERENCES cases(id),
  version                     INTEGER DEFAULT 1,
  parsed_at                   TIMESTAMP WITH TIME ZONE DEFAULT now(),
  tenant_legal_name           VARCHAR,
  landlord_legal_name         VARCHAR,
  property_address            VARCHAR,
  lease_start_date            DATE,
  lease_end_date              DATE,
  deposit_amount              DECIMAL(10,2),
  notice_required_days        INTEGER,
  notice_method               VARCHAR,
  pet_policy                  VARCHAR,
  early_termination_clause    TEXT,
  maintenance_responsibilities TEXT,
  notice_compliant            BOOLEAN,
  flagged_clauses             JSONB,
  raw_parse_output            JSONB,
  confidence_score            DECIMAL(4,2)
);
```

---

## Migration 010 — agent_sessions

```sql
CREATE TABLE agent_sessions (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  case_id         UUID NOT NULL REFERENCES cases(id) ON DELETE CASCADE,
  session_type    VARCHAR NOT NULL,
  started_at      TIMESTAMP WITH TIME ZONE DEFAULT now(),
  completed_at    TIMESTAMP WITH TIME ZONE,
  status          VARCHAR DEFAULT 'running',
  input_summary   TEXT,
  output_summary  TEXT,
  error_message   TEXT,
  foundry_queries JSONB,
  tools_called    JSONB,
  tokens_used     INTEGER,
  model_version   VARCHAR
);

CREATE INDEX idx_sessions_case_id ON agent_sessions(case_id);
```

---

## Migration 011 — conversation_messages

```sql
CREATE TABLE conversation_messages (
  id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  case_id       UUID NOT NULL REFERENCES cases(id) ON DELETE CASCADE,
  session_id    UUID REFERENCES agent_sessions(id),
  role          VARCHAR NOT NULL,
  message_type  VARCHAR DEFAULT 'text',
  content       TEXT,
  form_schema   JSONB,
  form_response JSONB,
  created_at    TIMESTAMP WITH TIME ZONE DEFAULT now()
);

CREATE INDEX idx_messages_case_id ON conversation_messages(case_id);
```

---

## Migration 012 — timeline_events

```sql
CREATE TABLE timeline_events (
  id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  case_id                 UUID NOT NULL REFERENCES cases(id) ON DELETE CASCADE,
  event_type              VARCHAR NOT NULL,
  title                   VARCHAR NOT NULL,
  description             TEXT,
  event_date              DATE,
  is_deadline             BOOLEAN DEFAULT FALSE,
  deadline_alert_sent_at  TIMESTAMP WITH TIME ZONE,
  completed               BOOLEAN DEFAULT FALSE,
  completed_at            TIMESTAMP WITH TIME ZONE,
  document_id             UUID REFERENCES documents(id),
  source                  VARCHAR DEFAULT 'agent',
  created_at              TIMESTAMP WITH TIME ZONE DEFAULT now()
);

CREATE INDEX idx_timeline_case_id ON timeline_events(case_id);
CREATE INDEX idx_timeline_deadlines ON timeline_events(is_deadline, completed, event_date);
```

---

## Migration 013 — court_tracking

```sql
CREATE TABLE court_tracking (
  id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  case_id             UUID UNIQUE NOT NULL REFERENCES cases(id) ON DELETE CASCADE,
  court_name          VARCHAR,
  court_case_number   VARCHAR,
  court_portal_url    VARCHAR,
  last_checked        TIMESTAMP WITH TIME ZONE,
  check_frequency     INTEGER DEFAULT 360,
  last_status         VARCHAR,
  entries             JSONB,
  new_entries_found   BOOLEAN DEFAULT FALSE,
  alert_sent          BOOLEAN DEFAULT FALSE
);
```

---

## Migration 014 — law_freshness

```sql
CREATE TABLE law_freshness (
  id                    UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  state                 VARCHAR(2) UNIQUE NOT NULL,
  dispute_type          VARCHAR DEFAULT 'security_deposit',
  last_verified         TIMESTAMP WITH TIME ZONE,
  next_review           TIMESTAMP WITH TIME ZONE,
  review_frequency_days INTEGER DEFAULT 90,
  last_pipeline_run     TIMESTAMP WITH TIME ZONE,
  last_pipeline_status  VARCHAR,
  last_pipeline_changes JSONB,
  pending_review        BOOLEAN DEFAULT FALSE,
  foundry_source_id     VARCHAR,
  source_urls           JSONB
);

INSERT INTO law_freshness (state, dispute_type) VALUES
  ('TX', 'security_deposit'),
  ('CA', 'security_deposit'),
  ('FL', 'security_deposit');
```

---

## Migration 015 — notifications

```sql
CREATE TABLE notifications (
  id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id       UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  case_id       UUID REFERENCES cases(id),
  channel       VARCHAR NOT NULL,
  recipient     VARCHAR NOT NULL,
  message       TEXT,
  status        VARCHAR DEFAULT 'pending',
  provider_id   VARCHAR,
  error         TEXT,
  sent_at       TIMESTAMP WITH TIME ZONE,
  created_at    TIMESTAMP WITH TIME ZONE DEFAULT now()
);

CREATE INDEX idx_notifications_user_id ON notifications(user_id);
CREATE INDEX idx_notifications_case_id ON notifications(case_id);
```
