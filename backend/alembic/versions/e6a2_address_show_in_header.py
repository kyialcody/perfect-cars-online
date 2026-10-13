"""move header-address flag from contact_info to per-address contact_address

Revision ID: e6a2_address_show_in_header
Revises: d5f0_footer_settings
Create Date: 2026-06-27
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "e6a2_address_show_in_header"
down_revision = "d5f0_footer_settings"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "contact_address",
        sa.Column("show_in_header", sa.Boolean(), nullable=False, server_default="false"),
    )
    # Preserve current behaviour: if the old global toggle was on, mark the
    # first address (lowest id) as shown in the header.
    op.execute(
        """
        UPDATE contact_address
        SET show_in_header = true
        WHERE id = (SELECT MIN(id) FROM contact_address)
          AND EXISTS (
            SELECT 1 FROM contact_info
            WHERE show_address_in_header = true
            LIMIT 1
          )
        """
    )
    op.drop_column("contact_info", "show_address_in_header")


def downgrade() -> None:
    op.add_column(
        "contact_info",
        sa.Column("show_address_in_header", sa.Boolean(), nullable=False, server_default="true"),
    )
    op.drop_column("contact_address", "show_in_header")
