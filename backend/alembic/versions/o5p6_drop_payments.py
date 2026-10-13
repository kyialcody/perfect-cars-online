"""drop booking, payment_event and lead prepayment/booking columns

On-site payment and prepayment are removed: leads keep their statuses
(new/in_progress/approved/rejected/done) but no booking or prepayment happens
on the site anymore.

Revision ID: o5p6_drop_payments
Revises: n4o5_drop_credit_tables
Create Date: 2026-07-06 14:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "o5p6_drop_payments"
down_revision: Union[str, None] = "n4o5_drop_credit_tables"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_column("lead", "approved_prepayment_amount")
    op.drop_column("lead", "booking_id")
    op.drop_table("payment_event")
    op.drop_index("ix_booking_payment_external_id", table_name="booking")
    op.drop_table("booking")
    postgresql.ENUM(name="booking_status").drop(op.get_bind(), checkfirst=True)


def downgrade() -> None:
    booking_status = postgresql.ENUM(
        "created",
        "awaiting_payment",
        "paid",
        "failed",
        "cancelled",
        "refunded",
        name="booking_status",
        create_type=False,
    )
    booking_status.create(op.get_bind(), checkfirst=True)
    op.create_table(
        "booking",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("public_id", sa.String(length=32), nullable=False),
        sa.Column("car_id", sa.Integer(), nullable=True),
        sa.Column("customer_name", sa.String(length=120), nullable=False),
        sa.Column("customer_phone", sa.String(length=20), nullable=False),
        sa.Column("customer_email", sa.String(length=255), nullable=True),
        sa.Column("consent", sa.Boolean(), nullable=False),
        sa.Column("status", booking_status, nullable=False),
        sa.Column("amount_total", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("amount_prepayment", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("provider", sa.String(length=40), nullable=False),
        sa.Column("payment_external_id", sa.String(length=120), nullable=True),
        sa.Column("payment_url", sa.String(length=500), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["car_id"], ["car.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("public_id"),
        sa.UniqueConstraint("provider", "payment_external_id", name="uq_booking_provider_payment"),
    )
    op.create_index("ix_booking_payment_external_id", "booking", ["payment_external_id"])
    op.create_table(
        "payment_event",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("provider", sa.String(length=40), nullable=False),
        sa.Column("event_id", sa.String(length=120), nullable=False),
        sa.Column("booking_id", sa.Integer(), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["booking_id"], ["booking.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("provider", "event_id", name="uq_payment_event"),
    )
    op.add_column("lead", sa.Column("booking_id", sa.Integer(), nullable=True))
    op.create_foreign_key(
        None, "lead", "booking", ["booking_id"], ["id"], ondelete="SET NULL"
    )
    op.add_column(
        "lead",
        sa.Column("approved_prepayment_amount", sa.Numeric(precision=12, scale=2), nullable=True),
    )
