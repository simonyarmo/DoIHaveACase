"""add unique constraint on lease_parse_results.document_id

Revision ID: 017
Revises: 016
Create Date: 2026-06-12 00:00:00

"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "017"
down_revision: Union[str, None] = "016"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        "ALTER TABLE lease_parse_results ADD CONSTRAINT uq_lease_parse_results_document_id UNIQUE (document_id)"
    )


def downgrade() -> None:
    op.execute("ALTER TABLE lease_parse_results DROP CONSTRAINT IF EXISTS uq_lease_parse_results_document_id")
