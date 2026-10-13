"""Add publication status to cars.

Existing cars are backfilled to ``published`` so the live catalog keeps
showing them; new cars default to ``draft`` until assembled in the wizard.

Revision ID: d4e7_car_status
Revises: c9d1_card_source_car
Create Date: 2026-06-25 10:30:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "d4e7_car_status"
down_revision = "c9d1_card_source_car"
branch_labels = None
depends_on = None


def upgrade() -> None:
    car_status = postgresql.ENUM(
        "draft", "published", "hidden", name="car_status", create_type=False
    )
    car_status.create(op.get_bind(), checkfirst=True)
    op.add_column(
        "car",
        sa.Column(
            "status",
            car_status,
            nullable=False,
            server_default="draft",
        ),
    )
    # Backfill: everything that already exists was live, so keep it visible.
    op.execute("UPDATE car SET status = 'published'")


def downgrade() -> None:
    op.drop_column("car", "status")
    postgresql.ENUM(name="car_status").drop(op.get_bind(), checkfirst=True)
