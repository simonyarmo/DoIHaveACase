"""create timeline_events table

Revision ID: 012
Revises: 011
Create Date: 2026-01-01 00:00:11

"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "012"
down_revision: Union[str, None] = "011"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("""
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
        )
    """)
    op.execute('CREATE INDEX idx_timeline_case_id ON timeline_events(case_id)')
    op.execute('CREATE INDEX idx_timeline_deadlines ON timeline_events(is_deadline, completed, event_date)')


def downgrade() -> None:
    op.execute('DROP TABLE IF EXISTS timeline_events')
