"""credit page settings and gifts

Revision ID: g8c1_credit_page
Revises: f7b3_car_used_specs
Create Date: 2026-06-27
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "g8c1_credit_page"
down_revision = "f7b3_car_used_specs"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "credit_page_settings",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("banner_url", sa.String(length=500), nullable=True),
        sa.Column("installment_percent", sa.Float(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "credit_gift",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("credit_gift")
    op.drop_table("credit_page_settings")
