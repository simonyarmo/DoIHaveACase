"""create conversation_messages table

Revision ID: 011
Revises: 010
Create Date: 2026-01-01 00:00:10

"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "011"
down_revision: Union[str, None] = "010"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("""
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
        )
    """)
    op.execute('CREATE INDEX idx_messages_case_id ON conversation_messages(case_id)')


def downgrade() -> None:
    op.execute('DROP TABLE IF EXISTS conversation_messages')
