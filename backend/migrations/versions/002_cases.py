"""create cases table and enums

Revision ID: 002
Revises: 001
Create Date: 2026-01-01 00:00:01

"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("""
        CREATE TYPE case_status AS ENUM (
          'intake', 'researching', 'assessment', 'action_plan',
          'demand_sent', 'filed', 'hearing_scheduled', 'resolved',
          'closed_no_case'
        )
    """)
    op.execute("""
        CREATE TYPE dispute_type AS ENUM (
          'security_deposit',
          'habitability',
          'lease_violation'
        )
    """)
    op.execute("""
        CREATE TYPE resolution_type AS ENUM (
          'settled', 'won', 'lost', 'withdrawn', 'no_case'
        )
    """)
    op.execute("""
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
        )
    """)
    op.execute('CREATE INDEX idx_cases_user_id ON cases(user_id)')


def downgrade() -> None:
    op.execute('DROP TABLE IF EXISTS cases')
    op.execute('DROP TYPE IF EXISTS resolution_type')
    op.execute('DROP TYPE IF EXISTS dispute_type')
    op.execute('DROP TYPE IF EXISTS case_status')
