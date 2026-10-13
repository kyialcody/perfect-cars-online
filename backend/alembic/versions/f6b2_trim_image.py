"""Add a per-trim banner photo.

Each комплектация can carry its own photo, shown in that trim's block on the
detail card (issue #72 follow-up). Stored as an S3 object key, nullable.

Revision ID: f6b2_trim_image
Revises: e5a1_car_is_hidden
Create Date: 2026-06-25 13:00:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "f6b2_trim_image"
down_revision = "e5a1_car_is_hidden"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("trim", sa.Column("image_url", sa.String(length=500), nullable=True))


def downgrade() -> None:
    op.drop_column("trim", "image_url")
