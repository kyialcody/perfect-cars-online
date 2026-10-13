"""Replace car publication status with a plain is_hidden flag.

R1 refactor (issue #72): the 3-state ``car_status`` enum (draft/published/
hidden) collapses to a boolean ``is_hidden``. A car is now public unless the
admin hides it — there is no draft stage. Backfill: previously ``hidden`` cars
stay hidden; everything else (draft/published) becomes visible.

Revision ID: e5a1_car_is_hidden
Revises: d4e7_car_status
Create Date: 2026-06-25 12:00:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "e5a1_car_is_hidden"
down_revision = "d4e7_car_status"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "car",
        sa.Column(
            "is_hidden",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )
    # Only admin-hidden cars carry over as hidden; drafts become visible too.
    op.execute("UPDATE car SET is_hidden = true WHERE status = 'hidden'")
    op.drop_column("car", "status")
    postgresql.ENUM(name="car_status").drop(op.get_bind(), checkfirst=True)


def downgrade() -> None:
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
    # Hidden cars round-trip to ``hidden``; visible ones to ``published``.
    # Cast the literals to the enum — Postgres won't coerce text implicitly.
    op.execute(
        "UPDATE car SET status = "
        "(CASE WHEN is_hidden THEN 'hidden' ELSE 'published' END)::car_status"
    )
    op.drop_column("car", "is_hidden")
