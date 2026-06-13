"""add assessment fields to case_details_security_deposit

Revision ID: 019
Revises: 018
Create Date: 2026-06-13 00:00:00

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "019"
down_revision: Union[str, None] = "018"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("case_details_security_deposit", sa.Column("case_strength", sa.String(), nullable=True))
    op.add_column("case_details_security_deposit", sa.Column("findings_good", postgresql.JSONB(), nullable=True))
    op.add_column("case_details_security_deposit", sa.Column("findings_caution", postgresql.JSONB(), nullable=True))
    op.add_column("case_details_security_deposit", sa.Column("findings_bad", postgresql.JSONB(), nullable=True))
    op.add_column("case_details_security_deposit", sa.Column("defenses_likely", postgresql.JSONB(), nullable=True))
    op.add_column("case_details_security_deposit", sa.Column("exceeds_jurisdiction", sa.Boolean(), nullable=True))
    op.add_column("case_details_security_deposit", sa.Column("jurisdiction_options", postgresql.JSONB(), nullable=True))
    op.add_column("case_details_security_deposit", sa.Column("recommended_path", sa.Text(), nullable=True))
    op.add_column("case_details_security_deposit", sa.Column("notice_compliant", sa.Boolean(), nullable=True))
    op.add_column("case_details_security_deposit", sa.Column("notice_risk_amount", sa.Numeric(10, 2), nullable=True))


def downgrade() -> None:
    op.drop_column("case_details_security_deposit", "notice_risk_amount")
    op.drop_column("case_details_security_deposit", "notice_compliant")
    op.drop_column("case_details_security_deposit", "recommended_path")
    op.drop_column("case_details_security_deposit", "jurisdiction_options")
    op.drop_column("case_details_security_deposit", "exceeds_jurisdiction")
    op.drop_column("case_details_security_deposit", "defenses_likely")
    op.drop_column("case_details_security_deposit", "findings_bad")
    op.drop_column("case_details_security_deposit", "findings_caution")
    op.drop_column("case_details_security_deposit", "findings_good")
    op.drop_column("case_details_security_deposit", "case_strength")
