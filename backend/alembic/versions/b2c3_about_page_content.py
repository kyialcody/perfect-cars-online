"""about page content: text, salon photos, bank partners

Revision ID: b2c3_about_page_content
Revises: a1b2_homepage_v2
Create Date: 2026-06-26
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "b2c3_about_page_content"
down_revision = "a1b2_homepage_v2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("home_about", sa.Column("page_text", sa.Text(), nullable=True))

    op.create_table(
        "about_salon_photo",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("image_url", sa.String(500), nullable=True),
        sa.Column("alt", sa.String(160), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
    )

    op.create_table(
        "bank_partner",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(160), nullable=False),
        sa.Column("logo_url", sa.String(500), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("bank_partner")
    op.drop_table("about_salon_photo")
    op.drop_column("home_about", "page_text")
