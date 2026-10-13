"""car benefits

Revision ID: b8f2_car_benefits
Revises: f44_home_content_blocks
Create Date: 2026-06-25 00:00:00.000000
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "b8f2_car_benefits"
down_revision = "f44_home_content_blocks"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "car_benefit",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("car_id", sa.Integer(), nullable=False),
        sa.Column("icon", sa.String(length=40), nullable=False),
        sa.Column("text", sa.String(length=160), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(["car_id"], ["car.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("car_benefit")
