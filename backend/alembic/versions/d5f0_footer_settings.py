"""footer settings: requisites, social links, footer text, header address toggle

Revision ID: d5f0_footer_settings
Revises: c4e8_contacts_page_content
Create Date: 2026-06-27
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "d5f0_footer_settings"
down_revision = "c4e8_contacts_page_content"
branch_labels = None
depends_on = None


def _timestamps() -> list[sa.Column]:
    return [
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
    ]


def upgrade() -> None:
    op.add_column("contact_info", sa.Column("footer_about_text", sa.Text(), nullable=True))
    op.add_column(
        "contact_info",
        sa.Column("show_address_in_header", sa.Boolean(), nullable=False, server_default="true"),
    )

    op.create_table(
        "requisite",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("label", sa.String(200), nullable=False),
        sa.Column("value", sa.Text(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        *_timestamps(),
    )

    op.create_table(
        "social_link",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("kind", sa.String(40), nullable=False),
        sa.Column("url", sa.String(500), nullable=True),
        sa.Column("icon_url", sa.String(500), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        *_timestamps(),
    )


def downgrade() -> None:
    op.drop_table("social_link")
    op.drop_table("requisite")
    op.drop_column("contact_info", "show_address_in_header")
    op.drop_column("contact_info", "footer_about_text")
