"""Response schemas for the public spare-parts API."""
from __future__ import annotations

import enum
from decimal import Decimal

from pydantic import BaseModel

from app.models.parts import PartCondition, PartKind


class PartSort(str, enum.Enum):
    newest = "newest"
    price_asc = "price_asc"
    price_desc = "price_desc"


class PartListItem(BaseModel):
    """One card in the parts grid (mirrors the used-car card shape)."""

    id: int
    slug: str
    name: str
    condition: PartCondition
    kind: PartKind
    category: str | None
    category_slug: str | None
    brand: str | None
    brand_slug: str | None
    manufacturer: str | None
    part_number: str | None

    price: Decimal
    price_old: Decimal | None
    benefit_badge: str | None
    status_text: str | None

    in_stock: bool
    qty: int
    image_url: str | None


class PartListResponse(BaseModel):
    items: list[PartListItem]
    total: int
    page: int
    page_size: int
    pages: int


class PartCountResponse(BaseModel):
    count: int


class PartImageOut(BaseModel):
    url: str | None
    is_main: bool
    sort_order: int


class PartDetail(PartListItem):
    description: str | None
    images: list[PartImageOut]
    similar: list[PartListItem]


# --- Filter options ----------------------------------------------------------


class PartRefOption(BaseModel):
    slug: str
    name: str


class PartBrandOption(BaseModel):
    slug: str
    name: str
    logo_url: str | None = None


class PartEnumOption(BaseModel):
    value: str
    name: str


class PartFiltersResponse(BaseModel):
    categories: list[PartRefOption]
    brands: list[PartBrandOption]
    manufacturers: list[str]
    conditions: list[PartEnumOption]
    kinds: list[PartEnumOption]
