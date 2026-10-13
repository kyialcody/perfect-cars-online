"""home content blocks

Revision ID: f44_home_content_blocks
Revises: a1f4c9e2b8d7
Create Date: 2026-06-24 04:50:00.000000
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op


revision = "f44_home_content_blocks"
down_revision = "a1f4c9e2b8d7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "home_promo",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("slug", sa.String(length=120), nullable=False),
        sa.Column("title", sa.String(length=220), nullable=False),
        sa.Column("subtitle", sa.String(length=240), nullable=True),
        sa.Column("badge_text", sa.String(length=120), nullable=True),
        sa.Column("button_text", sa.String(length=80), nullable=True),
        sa.Column("button_url", sa.String(length=300), nullable=True),
        sa.Column("image_url", sa.String(length=500), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("slug"),
    )
    op.create_table(
        "home_collection",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("slug", sa.String(length=120), nullable=False),
        sa.Column("title", sa.String(length=160), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("button_text", sa.String(length=80), nullable=True),
        sa.Column("button_url", sa.String(length=300), nullable=True),
        sa.Column("image_url", sa.String(length=500), nullable=True),
        sa.Column("car_id", sa.Integer(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["car_id"], ["car.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("slug"),
    )


def downgrade() -> None:
    op.drop_table("home_collection")
    op.drop_table("home_promo")
