"""homepage v2: HomeAbout, DealerLocation, HomeCollection.show_on_home

Revision ID: a1b2_homepage_v2
Revises: d2f8_petrol_consumption
Create Date: 2026-06-26
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "a1b2_homepage_v2"
down_revision = "d2f8_petrol_consumption"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "home_collection",
        sa.Column("show_on_home", sa.Boolean(), nullable=False, server_default="true"),
    )

    op.create_table(
        "home_about",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("video_url", sa.String(500), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
    )

    op.create_table(
        "dealer_location",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(160), nullable=False),
        sa.Column("address", sa.String(300), nullable=False),
        sa.Column("lat", sa.Float(), nullable=False),
        sa.Column("lng", sa.Float(), nullable=False),
        sa.Column("phone", sa.String(60), nullable=True),
        sa.Column("hours", sa.String(120), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("dealer_location")
    op.drop_table("home_about")
    op.drop_column("home_collection", "show_on_home")
