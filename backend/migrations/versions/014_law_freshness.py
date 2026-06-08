"""create law_freshness table and seed TX, CA, FL

Revision ID: 014
Revises: 013
Create Date: 2026-01-01 00:00:13

"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "014"
down_revision: Union[str, None] = "013"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("""
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
        )
    """)
    op.execute("""
        INSERT INTO law_freshness (state, dispute_type) VALUES
          ('TX', 'security_deposit'),
          ('CA', 'security_deposit'),
          ('FL', 'security_deposit')
    """)


def downgrade() -> None:
    op.execute('DROP TABLE IF EXISTS law_freshness')
