"""create case_expenses table

Revision ID: 008
Revises: 007
Create Date: 2026-01-01 00:00:07

"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "008"
down_revision: Union[str, None] = "007"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("""
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
        )
    """)
    op.execute('CREATE INDEX idx_expenses_case_id ON case_expenses(case_id)')


def downgrade() -> None:
    op.execute('DROP TABLE IF EXISTS case_expenses')
