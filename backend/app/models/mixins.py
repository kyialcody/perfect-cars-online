"""Reusable column mixins for ORM models."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import func
from sqlalchemy.orm import Mapped, mapped_column


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    # `onupdate` fires on ORM flushes only — bulk/raw SQL UPDATEs won't bump it.
    updated_at: Mapped[datetime] = mapped_column(
        server_default=func.now(), onupdate=func.now()
    )
