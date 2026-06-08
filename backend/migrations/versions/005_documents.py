"""create documents table

Revision ID: 005
Revises: 004
Create Date: 2026-01-01 00:00:04

"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "005"
down_revision: Union[str, None] = "004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE documents (
          id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
          case_id           UUID NOT NULL REFERENCES cases(id) ON DELETE CASCADE,
          type              VARCHAR NOT NULL,
          status            VARCHAR DEFAULT 'uploaded',
          version           INTEGER DEFAULT 1,
          parent_doc_id     UUID REFERENCES documents(id),
          storage_path      VARCHAR,
          foundry_source_id VARCHAR,
          file_name         VARCHAR,
          file_type         VARCHAR,
          file_size         INTEGER,
          uploaded_at       TIMESTAMP WITH TIME ZONE,
          generated_at      TIMESTAMP WITH TIME ZONE,
          approved_at       TIMESTAMP WITH TIME ZONE,
          exported_at       TIMESTAMP WITH TIME ZONE,
          filed_at          TIMESTAMP WITH TIME ZONE
        )
    """)
    op.execute('CREATE INDEX idx_documents_case_id ON documents(case_id)')


def downgrade() -> None:
    op.execute('DROP TABLE IF EXISTS documents')
