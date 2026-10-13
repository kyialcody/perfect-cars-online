"""Catalog domain models.

Schema for the car catalog (issue #4). Brands have models; a Car is a concrete
listing (new or used) of a Model, with trims, images, colors, spec features and
gifts. Body type / transmission / drive / engine type are reference tables
(справочники) so the admin can manage them.
"""
from __future__ import annotations

import enum
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    Column,
    Enum,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Table,
    UniqueConstraint,
    false,
    text,
)
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import TimestampMixin


class Condition(str, enum.Enum):
    new = "new"
    used = "used"
    # Marketing category: a hand-picked offer shown on the «Спецпредложения»
    # page. Orthogonal to the physical new/used split — a special offer is
    # edited with the same fields as a used car.
    special = "special"


class FeatureBlock(str, enum.Enum):
    safety = "safety"
    exterior = "exterior"
    interior = "interior"


# --- Reference tables (справочники) -----------------------------------------


class Brand(TimestampMixin, Base):
    __tablename__ = "brand"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120), unique=True)
    slug: Mapped[str] = mapped_column(String(120), unique=True)
    logo_url: Mapped[str | None] = mapped_column(String(500))

    models: Mapped[list["Model"]] = relationship(
        back_populates="brand", cascade="all, delete-orphan"
    )

    def __str__(self) -> str:
        return self.name


class Model(TimestampMixin, Base):
    __tablename__ = "model"
    __table_args__ = (UniqueConstraint("brand_id", "slug", name="uq_model_brand_slug"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    brand_id: Mapped[int] = mapped_column(ForeignKey("brand.id", ondelete="CASCADE"))
    name: Mapped[str] = mapped_column(String(120))
    slug: Mapped[str] = mapped_column(String(120))

    brand: Mapped["Brand"] = relationship(back_populates="models")
    cars: Mapped[list["Car"]] = relationship(back_populates="model")

    def __str__(self) -> str:
        # Brand is usually loaded in admin selects; fall back gracefully if not.
        brand = self.brand.name + " " if "brand" in self.__dict__ and self.brand else ""
        return f"{brand}{self.name}"


class BodyType(Base):
    __tablename__ = "body_type"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(80), unique=True)
    slug: Mapped[str] = mapped_column(String(80), unique=True)

    def __str__(self) -> str:
        return self.name


class Transmission(Base):
    __tablename__ = "transmission"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(80), unique=True)
    slug: Mapped[str] = mapped_column(String(80), unique=True)

    def __str__(self) -> str:
        return self.name


class Drive(Base):
    __tablename__ = "drive"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(80), unique=True)
    slug: Mapped[str] = mapped_column(String(80), unique=True)

    def __str__(self) -> str:
        return self.name


class EngineType(Base):
    __tablename__ = "engine_type"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(80), unique=True)
    slug: Mapped[str] = mapped_column(String(80), unique=True)

    def __str__(self) -> str:
        return self.name


class Color(Base):
    __tablename__ = "color"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(80), unique=True)
    hex: Mapped[str] = mapped_column(String(9))  # #RRGGBB[AA]

    def __str__(self) -> str:
        return self.name


# Car <-> Color (a listing is offered in several colors). Each activated colour
# also carries its own hero-banner image (1 colour = 1 banner picture).
car_color = Table(
    "car_color",
    Base.metadata,
    Column("car_id", ForeignKey("car.id", ondelete="CASCADE"), primary_key=True),
    Column("color_id", ForeignKey("color.id", ondelete="CASCADE"), primary_key=True),
    Column("image_url", String(500)),
)


# --- Car and its children ----------------------------------------------------


class Car(TimestampMixin, Base):
    __tablename__ = "car"

    id: Mapped[int] = mapped_column(primary_key=True)
    slug: Mapped[str] = mapped_column(String(160), unique=True)
    condition: Mapped[Condition] = mapped_column(Enum(Condition, name="condition"))

    model_id: Mapped[int] = mapped_column(ForeignKey("model.id"))
    body_type_id: Mapped[int | None] = mapped_column(ForeignKey("body_type.id"))
    engine_type_id: Mapped[int | None] = mapped_column(ForeignKey("engine_type.id"))
    # Car-level drive/transmission — mainly for used cars (a single specific
    # vehicle) where these aren't expressed via trims.
    drive_id: Mapped[int | None] = mapped_column(ForeignKey("drive.id"))
    transmission_id: Mapped[int | None] = mapped_column(ForeignKey("transmission.id"))
    source_car_id: Mapped[int | None] = mapped_column(ForeignKey("car.id", ondelete="SET NULL"))

    price: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    price_old: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    benefit_badge: Mapped[str | None] = mapped_column(String(120))
    status_text: Mapped[str | None] = mapped_column(String(160))

    # Catalog-grid preview image (S3 key), independent of the gallery. The big
    # detail banner is no longer a single image — it comes from the per-colour
    # banners on ``car_color`` (1 colour = 1 picture).
    card_image_url: Mapped[str | None] = mapped_column(String(500))

    # Spec icons on the card (mostly for new cars). ``fuel_consumption`` is the
    # electric figure (kWh, battery icon); ``fuel_consumption_petrol`` is the
    # petrol figure (L/100 km, fuel-pump icon). A hybrid fills both.
    power_hp: Mapped[int | None] = mapped_column(Integer)
    fuel_consumption: Mapped[Decimal | None] = mapped_column(Numeric(4, 1))
    fuel_consumption_petrol: Mapped[Decimal | None] = mapped_column(Numeric(4, 1))
    acceleration_0_100: Mapped[Decimal | None] = mapped_column(Numeric(4, 1))
    max_speed: Mapped[int | None] = mapped_column(Integer)

    # Used-only
    year: Mapped[int | None] = mapped_column(Integer)
    mileage: Mapped[int | None] = mapped_column(Integer)
    engine_volume: Mapped[Decimal | None] = mapped_column(Numeric(4, 1))

    in_stock: Mapped[bool] = mapped_column(Boolean, default=True)
    qty: Mapped[int] = mapped_column(Integer, default=1)
    is_promo: Mapped[bool] = mapped_column(Boolean, default=False)
    # Visibility — a car is shown on the public site unless the admin hides it.
    # New cars are visible immediately (one car = one form, no draft stage).
    is_hidden: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=false()
    )

    model: Mapped["Model"] = relationship(back_populates="cars")
    body_type: Mapped["BodyType | None"] = relationship()
    engine_type: Mapped["EngineType | None"] = relationship()
    drive: Mapped["Drive | None"] = relationship()
    transmission: Mapped["Transmission | None"] = relationship()
    source_car: Mapped["Car | None"] = relationship(
        remote_side=[id],
        back_populates="derived_cards",
        foreign_keys=[source_car_id],
    )
    derived_cards: Mapped[list["Car"]] = relationship(
        back_populates="source_car",
        foreign_keys=[source_car_id],
    )
    colors: Mapped[list["Color"]] = relationship(secondary=car_color)
    images: Mapped[list["CarImage"]] = relationship(
        back_populates="car", cascade="all, delete-orphan"
    )
    trims: Mapped[list["Trim"]] = relationship(
        back_populates="car", cascade="all, delete-orphan"
    )
    features: Mapped[list["CarFeature"]] = relationship(
        back_populates="car", cascade="all, delete-orphan"
    )
    benefits: Mapped[list["CarBenefit"]] = relationship(
        back_populates="car", cascade="all, delete-orphan"
    )
    gifts: Mapped[list["CarGift"]] = relationship(
        back_populates="car", cascade="all, delete-orphan"
    )

    @hybrid_property
    def is_public(self) -> bool:
        """Single source of truth for «visible on the public site».

        Works both on an instance (``car.is_public``) and as a SQL predicate
        (``select(Car).where(Car.is_public)``) so every public query and guard
        gates on the same rule.
        """
        return not self.is_hidden

    @is_public.expression
    def is_public(cls):
        return cls.is_hidden.is_(False)

    def __str__(self) -> str:
        model = self.model.name if "model" in self.__dict__ and self.model else "Авто"
        return f"#{self.id} {model} ({self.slug})"


class Trim(Base):
    """Комплектация — a row in the car's trims table."""

    __tablename__ = "trim"

    id: Mapped[int] = mapped_column(primary_key=True)
    car_id: Mapped[int] = mapped_column(ForeignKey("car.id", ondelete="CASCADE"))
    name: Mapped[str] = mapped_column(String(160))
    engine_volume: Mapped[Decimal | None] = mapped_column(Numeric(3, 1))
    power_hp: Mapped[int | None] = mapped_column(Integer)
    transmission_id: Mapped[int | None] = mapped_column(ForeignKey("transmission.id"))
    drive_id: Mapped[int | None] = mapped_column(ForeignKey("drive.id"))
    price: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    price_discount: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    # Own banner photo for this trim's block on the detail card (S3 object key).
    image_url: Mapped[str | None] = mapped_column(String(500))

    car: Mapped["Car"] = relationship(back_populates="trims")
    transmission: Mapped["Transmission | None"] = relationship()
    drive: Mapped["Drive | None"] = relationship()


class CarImage(Base):
    __tablename__ = "car_image"
    __table_args__ = (
        # At most one main image per car.
        Index(
            "uq_car_main_image",
            "car_id",
            unique=True,
            postgresql_where=text("is_main"),
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    car_id: Mapped[int] = mapped_column(ForeignKey("car.id", ondelete="CASCADE"))
    url: Mapped[str] = mapped_column(String(500))  # S3 object key / URL
    is_main: Mapped[bool] = mapped_column(Boolean, default=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)

    car: Mapped["Car"] = relationship(back_populates="images")


class CarFeature(Base):
    """A bullet in one of the Безопасность / Экстерьер / Интерьер blocks."""

    __tablename__ = "car_feature"

    id: Mapped[int] = mapped_column(primary_key=True)
    car_id: Mapped[int] = mapped_column(ForeignKey("car.id", ondelete="CASCADE"))
    block: Mapped[FeatureBlock] = mapped_column(Enum(FeatureBlock, name="feature_block"))
    text: Mapped[str] = mapped_column(String(300))
    sort_order: Mapped[int] = mapped_column(Integer, default=0)

    car: Mapped["Car"] = relationship(back_populates="features")


class CarBenefit(Base):
    """Marketing chip displayed in the detail hero."""

    __tablename__ = "car_benefit"

    id: Mapped[int] = mapped_column(primary_key=True)
    car_id: Mapped[int] = mapped_column(ForeignKey("car.id", ondelete="CASCADE"))
    icon: Mapped[str] = mapped_column(String(40))
    text: Mapped[str] = mapped_column(String(160))
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    car: Mapped["Car"] = relationship(back_populates="benefits")


class CarGift(Base):
    """Подарок при покупке (e.g. «Страхование в подарок»)."""

    __tablename__ = "car_gift"

    id: Mapped[int] = mapped_column(primary_key=True)
    car_id: Mapped[int] = mapped_column(ForeignKey("car.id", ondelete="CASCADE"))
    text: Mapped[str] = mapped_column(String(200))
    sort_order: Mapped[int] = mapped_column(Integer, default=0)

    car: Mapped["Car"] = relationship(back_populates="gifts")
