"""create court_tracking table

Revision ID: 013
Revises: 012
Create Date: 2026-01-01 00:00:12

"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "013"
down_revision: Union[str, None] = "012"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE court_tracking (
          id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
          case_id             UUID UNIQUE NOT NULL REFERENCES cases(id) ON DELETE CASCADE,
          court_name          VARCHAR,
          court_case_number   VARCHAR,
          court_portal_url    VARCHAR,
          last_checked        TIMESTAMP WITH TIME ZONE,
          check_frequency     INTEGER DEFAULT 360,
          last_status         VARCHAR,
          entries             JSONB,
          new_entries_found   BOOLEAN DEFAULT FALSE,
          alert_sent          BOOLEAN DEFAULT FALSE
        )
    """)


def downgrade() -> None:
    op.execute('DROP TABLE IF EXISTS court_tracking')
