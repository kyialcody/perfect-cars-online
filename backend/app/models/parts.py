"""Spare parts domain models.

Parallel to (but independent of) the car catalog: a Part is a concrete spare-part
listing with its own category, gallery and specs. It reuses the existing ``Brand``
table for «совместимая марка» (compatibility) so the parts page can offer the same
brand picker as the used-car page, but it is NOT tied to any ``Car`` row — parts are
added and edited on their own, mirroring the car add-flow only in shape.
"""
from __future__ import annotations

import enum
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    Enum,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    false,
    text,
)
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import TimestampMixin


class PartCondition(str, enum.Enum):
    new = "new"
    used = "used"


class PartKind(str, enum.Enum):
    """Оригинал vs аналог (aftermarket)."""

    original = "original"
    aftermarket = "aftermarket"


class PartCategory(Base):
    """Reference table (справочник): тормоза, подвеска, оптика, …"""

    __tablename__ = "part_category"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120), unique=True)
    slug: Mapped[str] = mapped_column(String(120), unique=True)

    parts: Mapped[list["Part"]] = relationship(back_populates="category")

    def __str__(self) -> str:
        return self.name


class Part(TimestampMixin, Base):
    __tablename__ = "part"

    id: Mapped[int] = mapped_column(primary_key=True)
    slug: Mapped[str] = mapped_column(String(180), unique=True)
    name: Mapped[str] = mapped_column(String(200))

    category_id: Mapped[int | None] = mapped_column(
        ForeignKey("part_category.id", ondelete="SET NULL")
    )
    # Reuse the car catalog's brand table for «совместимая марка».
    brand_id: Mapped[int | None] = mapped_column(
        ForeignKey("brand.id", ondelete="SET NULL")
    )

    condition: Mapped[PartCondition] = mapped_column(
        Enum(PartCondition, name="part_condition"), default=PartCondition.new
    )
    kind: Mapped[PartKind] = mapped_column(
        Enum(PartKind, name="part_kind"), default=PartKind.original
    )
    manufacturer: Mapped[str | None] = mapped_column(String(120))
    part_number: Mapped[str | None] = mapped_column(String(120))  # OEM / артикул

    price: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    price_old: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    benefit_badge: Mapped[str | None] = mapped_column(String(120))
    status_text: Mapped[str | None] = mapped_column(String(160))
    description: Mapped[str | None] = mapped_column(String(2000))

    card_image_url: Mapped[str | None] = mapped_column(String(500))

    in_stock: Mapped[bool] = mapped_column(Boolean, default=True)
    qty: Mapped[int] = mapped_column(Integer, default=1)
    is_hidden: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=false()
    )

    category: Mapped["PartCategory | None"] = relationship(back_populates="parts")
    brand: Mapped["Brand | None"] = relationship()  # noqa: F821
    images: Mapped[list["PartImage"]] = relationship(
        back_populates="part", cascade="all, delete-orphan"
    )

    @hybrid_property
    def is_public(self) -> bool:
        """Single source of truth for «visible on the public site»."""
        return not self.is_hidden

    @is_public.expression
    def is_public(cls):
        return cls.is_hidden.is_(False)

    def __str__(self) -> str:
        return f"#{self.id} {self.name} ({self.slug})"


class PartImage(Base):
    __tablename__ = "part_image"
    __table_args__ = (
        # At most one main image per part.
        Index(
            "uq_part_main_image",
            "part_id",
            unique=True,
            postgresql_where=text("is_main"),
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    part_id: Mapped[int] = mapped_column(ForeignKey("part.id", ondelete="CASCADE"))
    url: Mapped[str] = mapped_column(String(500))  # S3 object key / URL
    is_main: Mapped[bool] = mapped_column(Boolean, default=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)

    part: Mapped["Part"] = relationship(back_populates="images")
