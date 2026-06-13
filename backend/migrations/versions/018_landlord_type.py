"""add landlord_type to case_details_security_deposit

Revision ID: 018
Revises: 017
Create Date: 2026-06-12 00:00:00

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "018"
down_revision: Union[str, None] = "017"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("case_details_security_deposit", sa.Column("landlord_type", sa.String(), nullable=True))


def downgrade() -> None:
    op.drop_column("case_details_security_deposit", "landlord_type")
