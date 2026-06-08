"""create case_parties table

Revision ID: 004
Revises: 003
Create Date: 2026-01-01 00:00:03

"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "004"
down_revision: Union[str, None] = "003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("""
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
        )
    """)
    op.execute('CREATE INDEX idx_parties_case_id ON case_parties(case_id)')


def downgrade() -> None:
    op.execute('DROP TABLE IF EXISTS case_parties')
