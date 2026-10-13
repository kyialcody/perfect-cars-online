"""Lead capture model.

A Lead is a single request-a-call / callback submission from the public site
(issue #8). Leads are stored here, shown in the admin (issue #18) and pushed to
a Telegram bot on creation.
"""
from __future__ import annotations

import enum

from sqlalchemy import Boolean, Enum, ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import TimestampMixin


class LeadSource(str, enum.Enum):
    """Where on the site the lead was captured."""

    catalog = "catalog"
    car_detail = "car_detail"
    quick_pick = "quick_pick"
    footer = "footer"
    other = "other"


class LeadStatus(str, enum.Enum):
    new = "new"
    in_progress = "in_progress"
    approved = "approved"
    rejected = "rejected"
    done = "done"


class Lead(TimestampMixin, Base):
    __tablename__ = "lead"
    __table_args__ = (Index("ix_lead_user_dedupe", "user_id", "dedupe_key"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int | None] = mapped_column(
        ForeignKey("user_account.id", ondelete="SET NULL")
    )
    name: Mapped[str] = mapped_column(String(120))
    phone: Mapped[str] = mapped_column(String(20))  # normalized to +7XXXXXXXXXX
    source: Mapped[LeadSource] = mapped_column(
        Enum(LeadSource, name="lead_source"), default=LeadSource.other
    )
    car_id: Mapped[int | None] = mapped_column(
        ForeignKey("car.id", ondelete="SET NULL")
    )
    source_title: Mapped[str | None] = mapped_column(String(200))
    dedupe_key: Mapped[str | None] = mapped_column(String(240))
    comment: Mapped[str | None] = mapped_column(String(500))
    consent: Mapped[bool] = mapped_column(Boolean)  # ПДн — must be True to submit
    status: Mapped[LeadStatus] = mapped_column(
        Enum(LeadStatus, name="lead_status"), default=LeadStatus.new
    )

    car: Mapped["Car | None"] = relationship()  # noqa: F821
    user: Mapped["User | None"] = relationship()  # noqa: F821
