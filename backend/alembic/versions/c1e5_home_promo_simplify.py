"""Simplify the homepage banner to a picture + link.

The hero banner is no longer a text/button constructor: drop title, subtitle,
badge_text and button_text; ``button_url`` becomes ``link_url`` (the page the
banner opens on click). Image and link only (issue #72 follow-up).

Revision ID: c1e5_home_promo_simplify
Revises: b9d4_color_banner
Create Date: 2026-06-25 16:00:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "c1e5_home_promo_simplify"
down_revision = "b9d4_color_banner"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column("home_promo", "button_url", new_column_name="link_url")
    op.drop_column("home_promo", "title")
    op.drop_column("home_promo", "subtitle")
    op.drop_column("home_promo", "badge_text")
    op.drop_column("home_promo", "button_text")


def downgrade() -> None:
    op.add_column(
        "home_promo",
        sa.Column("title", sa.String(length=220), nullable=False, server_default=""),
    )
    op.add_column("home_promo", sa.Column("subtitle", sa.String(length=240), nullable=True))
    op.add_column("home_promo", sa.Column("badge_text", sa.String(length=120), nullable=True))
    op.add_column("home_promo", sa.Column("button_text", sa.String(length=80), nullable=True))
    op.alter_column("home_promo", "link_url", new_column_name="button_url")
