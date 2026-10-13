"""add 'special' value to condition enum

Revision ID: h9d2_condition_special
Revises: g8c1_credit_page
Create Date: 2026-06-28
"""
from __future__ import annotations

from alembic import op

revision = "h9d2_condition_special"
down_revision = "g8c1_credit_page"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # PostgreSQL keeps enum values in the type; add the new one idempotently.
    # ADD VALUE runs fine in a transaction on PG12+ as long as the value isn't
    # used in the same transaction (it isn't here).
    op.execute("ALTER TYPE condition ADD VALUE IF NOT EXISTS 'special'")


def downgrade() -> None:
    # PostgreSQL can't drop a single enum value; removing it would require
    # recreating the type. The extra value is harmless, so this is a no-op.
    pass
