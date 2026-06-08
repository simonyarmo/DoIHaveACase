-- Run these against the Supabase project after `alembic upgrade head`.
-- Supabase enforces RLS using auth.uid() from the verified JWT.
--
-- IMPORTANT: these policies protect data accessed via Supabase's PostgREST /
-- client-side APIs (where auth.uid() is populated from the request's JWT).
-- They do NOT protect this app's FastAPI backend: the backend connects to
-- Postgres directly as the `postgres` role (see DATABASE_URL), which owns
-- these tables and bypasses RLS entirely, and auth.uid() resolves to NULL on
-- that connection. The backend MUST continue to enforce authorization itself
-- (e.g. filtering every query by `Case.user_id == current_user.id`) — RLS
-- here is a safety net for direct/PostgREST access only, not a substitute.

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

-- Apply the same case-ownership pattern to all case-linked tables
ALTER TABLE case_details_security_deposit ENABLE ROW LEVEL SECURITY;
CREATE POLICY "case_details_security_deposit_own_data" ON case_details_security_deposit
  FOR ALL USING (
    case_id IN (
      SELECT c.id FROM cases c JOIN users u ON c.user_id = u.id WHERE auth.uid()::text = u.id::text
    )
  );

ALTER TABLE documents ENABLE ROW LEVEL SECURITY;
CREATE POLICY "documents_own_data" ON documents
  FOR ALL USING (
    case_id IN (
      SELECT c.id FROM cases c JOIN users u ON c.user_id = u.id WHERE auth.uid()::text = u.id::text
    )
  );

ALTER TABLE evidence ENABLE ROW LEVEL SECURITY;
CREATE POLICY "evidence_own_data" ON evidence
  FOR ALL USING (
    case_id IN (
      SELECT c.id FROM cases c JOIN users u ON c.user_id = u.id WHERE auth.uid()::text = u.id::text
    )
  );

ALTER TABLE timeline_events ENABLE ROW LEVEL SECURITY;
CREATE POLICY "timeline_events_own_data" ON timeline_events
  FOR ALL USING (
    case_id IN (
      SELECT c.id FROM cases c JOIN users u ON c.user_id = u.id WHERE auth.uid()::text = u.id::text
    )
  );

ALTER TABLE case_expenses ENABLE ROW LEVEL SECURITY;
CREATE POLICY "case_expenses_own_data" ON case_expenses
  FOR ALL USING (
    case_id IN (
      SELECT c.id FROM cases c JOIN users u ON c.user_id = u.id WHERE auth.uid()::text = u.id::text
    )
  );

ALTER TABLE conversation_messages ENABLE ROW LEVEL SECURITY;
CREATE POLICY "conversation_messages_own_data" ON conversation_messages
  FOR ALL USING (
    case_id IN (
      SELECT c.id FROM cases c JOIN users u ON c.user_id = u.id WHERE auth.uid()::text = u.id::text
    )
  );

ALTER TABLE agent_sessions ENABLE ROW LEVEL SECURITY;
CREATE POLICY "agent_sessions_own_data" ON agent_sessions
  FOR ALL USING (
    case_id IN (
      SELECT c.id FROM cases c JOIN users u ON c.user_id = u.id WHERE auth.uid()::text = u.id::text
    )
  );

ALTER TABLE case_parties ENABLE ROW LEVEL SECURITY;
CREATE POLICY "case_parties_own_data" ON case_parties
  FOR ALL USING (
    case_id IN (
      SELECT c.id FROM cases c JOIN users u ON c.user_id = u.id WHERE auth.uid()::text = u.id::text
    )
  );
