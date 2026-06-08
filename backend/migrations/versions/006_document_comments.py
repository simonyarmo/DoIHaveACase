"""create document_comments table

Revision ID: 006
Revises: 005
Create Date: 2026-01-01 00:00:05

"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "006"
down_revision: Union[str, None] = "005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE document_comments (
          id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
          document_id     UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
          comment_type    VARCHAR NOT NULL,
          section_ref     VARCHAR,
          comment_text    TEXT,
          original_text   TEXT,
          new_text        TEXT,
          resolved        BOOLEAN DEFAULT FALSE,
          resolved_at     TIMESTAMP WITH TIME ZONE,
          resolution_text TEXT,
          created_at      TIMESTAMP WITH TIME ZONE DEFAULT now()
        )
    """)
    op.execute('CREATE INDEX idx_comments_document_id ON document_comments(document_id)')


def downgrade() -> None:
    op.execute('DROP TABLE IF EXISTS document_comments')
