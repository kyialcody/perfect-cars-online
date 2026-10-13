"""contacts page content: info, phones, addresses, photos

Revision ID: c4e8_contacts_page_content
Revises: b2c3_about_page_content
Create Date: 2026-06-27
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "c4e8_contacts_page_content"
down_revision = "b2c3_about_page_content"
branch_labels = None
depends_on = None


def _timestamps() -> list[sa.Column]:
    return [
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
    ]


def upgrade() -> None:
    op.create_table(
        "contact_info",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("about_text", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        *_timestamps(),
    )

    op.create_table(
        "contact_phone",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("value", sa.String(60), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        *_timestamps(),
    )

    op.create_table(
        "contact_address",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("value", sa.String(300), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        *_timestamps(),
    )

    op.create_table(
        "contact_photo",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("image_url", sa.String(500), nullable=True),
        sa.Column("alt", sa.String(160), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        *_timestamps(),
    )


def downgrade() -> None:
    op.drop_table("contact_photo")
    op.drop_table("contact_address")
    op.drop_table("contact_phone")
    op.drop_table("contact_info")
