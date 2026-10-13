"""lead approved prepayment amount

Revision ID: k2l3_lead_approved_prepayment
Revises: j1k2_profile_leads
Create Date: 2026-06-28 13:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "k2l3_lead_approved_prepayment"
down_revision: Union[str, None] = "j1k2_profile_leads"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "lead",
        sa.Column("approved_prepayment_amount", sa.Numeric(12, 2), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("lead", "approved_prepayment_amount")
