"""User account model for optional public registration (issue #10).

Registration is optional (guests can still book); accounts are blocked for
``@gmail.com`` per the project's legal constraint — enforced in the API layer.
"""
from __future__ import annotations

from sqlalchemy import Boolean, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.mixins import TimestampMixin


class User(TimestampMixin, Base):
    __tablename__ = "user_account"  # avoid the reserved word "user" in Postgres

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True)  # stored lower-case
    password_hash: Mapped[str] = mapped_column(String(255))
    full_name: Mapped[str | None] = mapped_column(String(120))
    phone: Mapped[str | None] = mapped_column(String(20))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    # Grants access to the SQLAdmin panel (issue #18). Set server-side only —
    # public registration never sets this.
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")

    def __str__(self) -> str:
        label = self.full_name or self.email
        return f"{label} ({self.email})" if self.full_name else label
