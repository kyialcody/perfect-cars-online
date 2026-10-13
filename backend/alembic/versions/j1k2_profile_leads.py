"""profile leads and user phone

Revision ID: j1k2_profile_leads
Revises: h9d2_condition_special
Create Date: 2026-06-28 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "j1k2_profile_leads"
down_revision: Union[str, None] = "h9d2_condition_special"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("user_account", sa.Column("phone", sa.String(length=20), nullable=True))
    op.add_column("booking", sa.Column("payment_url", sa.String(length=500), nullable=True))

    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute(
            """
            DO $$
            BEGIN
                IF NOT EXISTS (
                    SELECT 1 FROM pg_enum
                    WHERE enumlabel = 'approved'
                    AND enumtypid = 'lead_status'::regtype
                ) THEN
                    ALTER TYPE lead_status ADD VALUE 'approved';
                END IF;
                IF NOT EXISTS (
                    SELECT 1 FROM pg_enum
                    WHERE enumlabel = 'rejected'
                    AND enumtypid = 'lead_status'::regtype
                ) THEN
                    ALTER TYPE lead_status ADD VALUE 'rejected';
                END IF;
            END $$;
            """
        )

    op.add_column("lead", sa.Column("user_id", sa.Integer(), nullable=True))
    op.add_column("lead", sa.Column("booking_id", sa.Integer(), nullable=True))
    op.add_column("lead", sa.Column("source_title", sa.String(length=200), nullable=True))
    op.add_column("lead", sa.Column("dedupe_key", sa.String(length=240), nullable=True))
    op.create_foreign_key(
        "fk_lead_user_id_user_account",
        "lead",
        "user_account",
        ["user_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        "fk_lead_booking_id_booking",
        "lead",
        "booking",
        ["booking_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index("ix_lead_user_dedupe", "lead", ["user_id", "dedupe_key"])


def downgrade() -> None:
    op.drop_index("ix_lead_user_dedupe", table_name="lead")
    op.drop_constraint("fk_lead_booking_id_booking", "lead", type_="foreignkey")
    op.drop_constraint("fk_lead_user_id_user_account", "lead", type_="foreignkey")
    op.drop_column("lead", "dedupe_key")
    op.drop_column("lead", "source_title")
    op.drop_column("lead", "booking_id")
    op.drop_column("lead", "user_id")
    op.drop_column("booking", "payment_url")
    op.drop_column("user_account", "phone")
