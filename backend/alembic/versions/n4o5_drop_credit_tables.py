"""drop credit page tables

The «Кредит и рассрочка» section is replaced by «Запчасти»; its settings and
gift tables are no longer used anywhere (models, API and admin removed).

Revision ID: n4o5_drop_credit_tables
Revises: m3n4_parts_schema
Create Date: 2026-07-06 13:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "n4o5_drop_credit_tables"
down_revision: Union[str, None] = "m3n4_parts_schema"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_table("credit_gift")
    op.drop_table("credit_page_settings")


def downgrade() -> None:
    op.create_table(
        "credit_page_settings",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("banner_url", sa.String(length=500), nullable=True),
        sa.Column(
            "installment_percent", sa.Float(), nullable=False, server_default=sa.text("12.0")
        ),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "credit_gift",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
