"""Add dedicated catalog + hero banner images to a car.

Independent of the gallery: ``card_image_url`` is the catalog-grid preview and
``hero_image_url`` is the big banner at the top of the detail card (issue #72
follow-up). Both are nullable S3 object keys.

Revision ID: a7c3_car_banner_images
Revises: f6b2_trim_image
Create Date: 2026-06-25 14:00:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "a7c3_car_banner_images"
down_revision = "f6b2_trim_image"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("car", sa.Column("card_image_url", sa.String(length=500), nullable=True))
    op.add_column("car", sa.Column("hero_image_url", sa.String(length=500), nullable=True))


def downgrade() -> None:
    op.drop_column("car", "hero_image_url")
    op.drop_column("car", "card_image_url")
