"""create evidence table

Revision ID: 007
Revises: 006
Create Date: 2026-01-01 00:00:06

"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "007"
down_revision: Union[str, None] = "006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("""
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
        )
    """)
    op.execute('CREATE INDEX idx_evidence_case_id ON evidence(case_id)')


def downgrade() -> None:
    op.execute('DROP TABLE IF EXISTS evidence')
