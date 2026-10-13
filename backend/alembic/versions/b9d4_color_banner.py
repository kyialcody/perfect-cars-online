"""Per-colour hero banner; drop the single car hero image.

The big detail banner is now driven by colours: each activated colour carries
its own banner picture on ``car_color.image_url`` (issue #72 follow-up). The
former single ``car.hero_image_url`` is removed.

Revision ID: b9d4_color_banner
Revises: a7c3_car_banner_images
Create Date: 2026-06-25 15:00:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "b9d4_color_banner"
down_revision = "a7c3_car_banner_images"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("car_color", sa.Column("image_url", sa.String(length=500), nullable=True))
    op.drop_column("car", "hero_image_url")


def downgrade() -> None:
    op.add_column("car", sa.Column("hero_image_url", sa.String(length=500), nullable=True))
    op.drop_column("car_color", "image_url")
