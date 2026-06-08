"""create notifications table

Revision ID: 015
Revises: 014
Create Date: 2026-01-01 00:00:14

"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "015"
down_revision: Union[str, None] = "014"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE notifications (
          id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
          user_id       UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
          case_id       UUID REFERENCES cases(id),
          channel       VARCHAR NOT NULL,
          recipient     VARCHAR NOT NULL,
          message       TEXT,
          status        VARCHAR DEFAULT 'pending',
          provider_id   VARCHAR,
          error         TEXT,
          sent_at       TIMESTAMP WITH TIME ZONE,
          created_at    TIMESTAMP WITH TIME ZONE DEFAULT now()
        )
    """)
    op.execute('CREATE INDEX idx_notifications_user_id ON notifications(user_id)')
    op.execute('CREATE INDEX idx_notifications_case_id ON notifications(case_id)')


def downgrade() -> None:
    op.execute('DROP TABLE IF EXISTS notifications')
