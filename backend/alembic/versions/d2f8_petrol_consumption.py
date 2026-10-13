"""Add a separate petrol fuel-consumption figure.

Electric range/consumption stays in ``fuel_consumption`` (kWh, battery icon);
``fuel_consumption_petrol`` holds the petrol figure (L/100 km, fuel-pump icon).
A hybrid car fills both (issue #72 follow-up).

Revision ID: d2f8_petrol_consumption
Revises: c1e5_home_promo_simplify
Create Date: 2026-06-26 09:00:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "d2f8_petrol_consumption"
down_revision = "c1e5_home_promo_simplify"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("car", sa.Column("fuel_consumption_petrol", sa.Numeric(4, 1), nullable=True))


def downgrade() -> None:
    op.drop_column("car", "fuel_consumption_petrol")
