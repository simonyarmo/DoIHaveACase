"""create lease_parse_results table

Revision ID: 009
Revises: 008
Create Date: 2026-01-01 00:00:08

"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "009"
down_revision: Union[str, None] = "008"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("""
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
        )
    """)


def downgrade() -> None:
    op.execute('DROP TABLE IF EXISTS lease_parse_results')
