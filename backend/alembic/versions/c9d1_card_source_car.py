"""Track source car for admin-created cards.

Revision ID: c9d1_card_source_car
Revises: b8f2_car_benefits
Create Date: 2026-06-25 09:35:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "c9d1_card_source_car"
down_revision = "b8f2_car_benefits"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("car", sa.Column("source_car_id", sa.Integer(), nullable=True))
    op.create_foreign_key(
        "fk_car_source_car_id_car",
        "car",
        "car",
        ["source_car_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint("fk_car_source_car_id_car", "car", type_="foreignkey")
    op.drop_column("car", "source_car_id")
