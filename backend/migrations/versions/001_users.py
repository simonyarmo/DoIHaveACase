"""create users table

Revision ID: 001
Revises:
Create Date: 2026-01-01 00:00:00

"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute('CREATE EXTENSION IF NOT EXISTS pgcrypto')
    op.execute("""
        CREATE TABLE users (
          id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
          email               VARCHAR UNIQUE NOT NULL,
          full_name           VARCHAR NOT NULL,
          phone_number        VARCHAR,
          phone_verified      BOOLEAN DEFAULT FALSE,
          sms_notifications   BOOLEAN DEFAULT TRUE,
          notification_prefs  JSONB DEFAULT '{
            "deadlines": true,
            "court_updates": true,
            "documents": true,
            "seven_day_warning": true,
            "one_day_warning": true
          }',
          subscription_tier   VARCHAR DEFAULT 'free',
          created_at          TIMESTAMP WITH TIME ZONE DEFAULT now(),
          last_active         TIMESTAMP WITH TIME ZONE
        )
    """)


def downgrade() -> None:
    op.execute('DROP TABLE IF EXISTS users')
