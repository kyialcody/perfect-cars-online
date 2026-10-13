"""parts schema

Revision ID: m3n4_parts_schema
Revises: k2l3_lead_approved_prepayment
Create Date: 2026-07-06 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "m3n4_parts_schema"
down_revision: Union[str, None] = "k2l3_lead_approved_prepayment"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create enums up front (checkfirst so a lingering type from a partial run
    # doesn't abort). create_type=False on the columns avoids a second create.
    part_condition = postgresql.ENUM("new", "used", name="part_condition", create_type=False)
    part_kind = postgresql.ENUM(
        "original", "aftermarket", name="part_kind", create_type=False
    )
    part_condition.create(op.get_bind(), checkfirst=True)
    part_kind.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "part_category",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("slug", sa.String(length=120), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
        sa.UniqueConstraint("slug"),
    )
    op.create_table(
        "part",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("slug", sa.String(length=180), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("category_id", sa.Integer(), nullable=True),
        sa.Column("brand_id", sa.Integer(), nullable=True),
        sa.Column(
            "condition",
            postgresql.ENUM("new", "used", name="part_condition", create_type=False),
            nullable=False,
        ),
        sa.Column(
            "kind",
            postgresql.ENUM("original", "aftermarket", name="part_kind", create_type=False),
            nullable=False,
        ),
        sa.Column("manufacturer", sa.String(length=120), nullable=True),
        sa.Column("part_number", sa.String(length=120), nullable=True),
        sa.Column("price", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("price_old", sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column("benefit_badge", sa.String(length=120), nullable=True),
        sa.Column("status_text", sa.String(length=160), nullable=True),
        sa.Column("description", sa.String(length=2000), nullable=True),
        sa.Column("card_image_url", sa.String(length=500), nullable=True),
        sa.Column("in_stock", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("qty", sa.Integer(), nullable=False, server_default=sa.text("1")),
        sa.Column(
            "is_hidden", sa.Boolean(), nullable=False, server_default=sa.false()
        ),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["category_id"], ["part_category.id"], ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(["brand_id"], ["brand.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("slug"),
    )
    op.create_table(
        "part_image",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("part_id", sa.Integer(), nullable=False),
        sa.Column("url", sa.String(length=500), nullable=False),
        sa.Column("is_main", sa.Boolean(), nullable=True),
        sa.Column("sort_order", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["part_id"], ["part.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "uq_part_main_image",
        "part_image",
        ["part_id"],
        unique=True,
        postgresql_where=sa.text("is_main"),
    )


def downgrade() -> None:
    op.drop_index("uq_part_main_image", table_name="part_image")
    op.drop_table("part_image")
    op.drop_table("part")
    op.drop_table("part_category")
    postgresql.ENUM(name="part_kind").drop(op.get_bind(), checkfirst=True)
    postgresql.ENUM(name="part_condition").drop(op.get_bind(), checkfirst=True)
