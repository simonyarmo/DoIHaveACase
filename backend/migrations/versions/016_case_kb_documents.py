"""create case_kb_documents table

Revision ID: 016
Revises: 015
Create Date: 2026-06-12 00:00:00

"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "016"
down_revision: Union[str, None] = "015"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE case_kb_documents (
          id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
          case_id     UUID NOT NULL REFERENCES cases(id) ON DELETE CASCADE,
          doc_key     VARCHAR NOT NULL,
          title       VARCHAR NOT NULL,
          content     TEXT NOT NULL,
          doc_type    VARCHAR NOT NULL,
          created_at  TIMESTAMP WITH TIME ZONE DEFAULT now(),
          UNIQUE (case_id, doc_key)
        )
    """)
    op.execute("CREATE INDEX ix_case_kb_documents_case_id ON case_kb_documents (case_id)")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS case_kb_documents")
