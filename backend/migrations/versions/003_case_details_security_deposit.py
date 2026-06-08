"""create case_details_security_deposit table

Revision ID: 003
Revises: 002
Create Date: 2026-01-01 00:00:02

"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "003"
down_revision: Union[str, None] = "002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE case_details_security_deposit (
          id                          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
          case_id                     UUID UNIQUE NOT NULL REFERENCES cases(id) ON DELETE CASCADE,

          -- Property
          property_address            VARCHAR,
          property_state              VARCHAR(2),
          property_county             VARCHAR,
          property_type               VARCHAR,

          -- Landlord
          landlord_name_as_entered    VARCHAR,
          landlord_legal_name         VARCHAR,
          landlord_sos_verified       BOOLEAN DEFAULT FALSE,
          landlord_registered_agent   VARCHAR,
          landlord_address            VARCHAR,
          landlord_sos_status         VARCHAR,
          landlord_sos_lookup_date    TIMESTAMP WITH TIME ZONE,

          -- Deposit
          deposit_amount              DECIMAL(10,2),
          amount_returned             DECIMAL(10,2) DEFAULT 0,
          date_returned               DATE,
          move_in_date                DATE,
          move_out_date               DATE,
          keys_returned_date          DATE,
          forwarding_address          VARCHAR,
          forwarding_address_proof    BOOLEAN DEFAULT FALSE,

          -- Communication
          landlord_communication      VARCHAR DEFAULT 'none',
          itemization_received        BOOLEAN DEFAULT FALSE,
          itemization_date            DATE,
          demand_letter_sent          BOOLEAN DEFAULT FALSE,
          demand_letter_date          DATE,
          demand_letter_delivery      VARCHAR,

          -- Notice
          notice_provided             BOOLEAN,
          notice_date                 DATE,
          notice_method               VARCHAR,
          notice_days                 INTEGER,
          lease_required_notice_days  INTEGER,

          -- Computed (set by agent after research)
          days_overdue                INTEGER,
          deadline_date               DATE,
          violation_confirmed         BOOLEAN,
          bad_faith_indicators        JSONB,
          estimated_recovery_min      DECIMAL(10,2),
          estimated_recovery_max      DECIMAL(10,2),
          penalty_multiplier          DECIMAL(4,1)
        )
    """)


def downgrade() -> None:
    op.execute('DROP TABLE IF EXISTS case_details_security_deposit')
