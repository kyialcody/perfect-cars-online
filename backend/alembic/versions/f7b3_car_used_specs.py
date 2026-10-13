"""car-level drive, transmission and engine volume (used-car specs)

Revision ID: f7b3_car_used_specs
Revises: e6a2_address_show_in_header
Create Date: 2026-06-27
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "f7b3_car_used_specs"
down_revision = "e6a2_address_show_in_header"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("car", sa.Column("drive_id", sa.Integer(), nullable=True))
    op.add_column("car", sa.Column("transmission_id", sa.Integer(), nullable=True))
    op.add_column("car", sa.Column("engine_volume", sa.Numeric(4, 1), nullable=True))
    op.create_foreign_key("fk_car_drive", "car", "drive", ["drive_id"], ["id"])
    op.create_foreign_key("fk_car_transmission", "car", "transmission", ["transmission_id"], ["id"])


def downgrade() -> None:
    op.drop_constraint("fk_car_transmission", "car", type_="foreignkey")
    op.drop_constraint("fk_car_drive", "car", type_="foreignkey")
    op.drop_column("car", "engine_volume")
    op.drop_column("car", "transmission_id")
    op.drop_column("car", "drive_id")
