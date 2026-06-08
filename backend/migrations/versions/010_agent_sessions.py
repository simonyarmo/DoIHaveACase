"""create agent_sessions table

Revision ID: 010
Revises: 009
Create Date: 2026-01-01 00:00:09

"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "010"
down_revision: Union[str, None] = "009"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("""
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
        )
    """)
    op.execute('CREATE INDEX idx_sessions_case_id ON agent_sessions(case_id)')


def downgrade() -> None:
    op.execute('DROP TABLE IF EXISTS agent_sessions')
