"""Response schemas for the public catalog API."""
from __future__ import annotations

import enum
from decimal import Decimal

from pydantic import BaseModel, ConfigDict

from app.models.catalog import Condition


class CarSort(str, enum.Enum):
    """Sort options exposed on ``GET /cars``."""

    newest = "newest"
    price_asc = "price_asc"
    price_desc = "price_desc"
    year_desc = "year_desc"


class ColorOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    name: str
    hex: str
    # Per-car hero banner for this colour (browser URL); only set on car detail.
    image_url: str | None = None


class CarListItem(BaseModel):
    """One card in the catalog grid."""

    id: int
    slug: str
    condition: Condition
    brand: str
    brand_slug: str
    model: str
    model_slug: str
    title: str  # «Zeekr 001»

    price: Decimal
    price_old: Decimal | None
    benefit_badge: str | None
    status_text: str | None

    power_hp: int | None
    fuel_consumption: Decimal | None  # electric, kWh
    fuel_consumption_petrol: Decimal | None  # petrol, L/100 km
    acceleration_0_100: Decimal | None
    max_speed: int | None

    year: int | None
    mileage: int | None
    engine_volume: Decimal | None  # used cars, L

    body_type: str | None
    engine_type: str | None
    drive: str | None  # used cars
    transmission: str | None  # used cars

    in_stock: bool
    qty: int
    is_promo: bool

    image_url: str | None
    colors: list[ColorOut]


class CarListResponse(BaseModel):
    items: list[CarListItem]
    total: int
    page: int
    page_size: int
    pages: int


class CountResponse(BaseModel):
    count: int


class ImageOut(BaseModel):
    url: str  # browser-reachable URL
    is_main: bool
    sort_order: int


class TrimOut(BaseModel):
    """Комплектация row."""

    id: int
    name: str
    engine_volume: Decimal | None
    power_hp: int | None
    transmission: str | None
    drive: str | None
    price: Decimal
    price_discount: Decimal | None
    sort_order: int
    image_url: str | None  # browser-reachable URL, or None


class FeatureGroup(BaseModel):
    """Bullets for one of the Безопасность / Экстерьер / Интерьер blocks."""

    block: str
    items: list[str]


class BenefitOut(BaseModel):
    icon: str
    text: str
    sort_order: int


class CarDetail(CarListItem):
    """Full car card: everything in the list item plus child collections.

    ``colors`` here carry their per-colour hero banner (``image_url``); the big
    banner shown on the page is the active colour's picture.
    """

    images: list[ImageOut]
    trims: list[TrimOut]
    benefits: list[BenefitOut]
    features: list[FeatureGroup]
    gifts: list[str]
    similar: list[CarListItem]


# --- Filter options (GET /catalog/filters) ----------------------------------


class RefOption(BaseModel):
    """A reference value usable as a filter option."""

    slug: str
    name: str


class BrandOption(BaseModel):
    slug: str
    name: str
    logo_url: str | None  # browser-reachable URL


class ModelOption(BaseModel):
    slug: str
    name: str
    brand_slug: str


class FiltersResponse(BaseModel):
    """Everything the «Я ищу» block and the brand sidebar need to render."""

    brands: list[BrandOption]
    models: list[ModelOption]
    body_types: list[RefOption]
    transmissions: list[RefOption]
    drives: list[RefOption]
    engine_types: list[RefOption]
