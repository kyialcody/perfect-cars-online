"""Public spare-parts API: filtered, paginated, Redis-cached part listings.

Mirrors the car catalog API (``app.api.catalog``) but for the independent parts
domain. Like the catalog it does *not* use ``from __future__ import annotations``
so FastAPI can resolve the class-based query-param types at startup.
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import Select, case, func, literal, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload

from app.core.cache import (
    cache_get_json,
    cache_set_json,
    get_catalog_version,
    get_redis,
    make_key,
)
from app.core.storage import public_url
from app.db.deps import get_session
from app.models.catalog import Brand
from app.models.parts import Part, PartCategory, PartCondition, PartKind
from app.schemas.parts import (
    PartBrandOption,
    PartCountResponse,
    PartDetail,
    PartEnumOption,
    PartFiltersResponse,
    PartImageOut,
    PartListItem,
    PartListResponse,
    PartRefOption,
    PartSort,
)

# How many "similar" parts to attach to a part detail.
SIMILAR_LIMIT = 4

_CONDITION_LABELS = {PartCondition.new: "Новая", PartCondition.used: "Б/У"}
_KIND_LABELS = {PartKind.original: "Оригинал", PartKind.aftermarket: "Аналог"}

router = APIRouter(prefix="/parts", tags=["parts"])


class PartFilters:
    """Shared query parameters for parts listing and counting."""

    def __init__(
        self,
        category: str | None = Query(None, description="Category slug"),
        brand: str | None = Query(None, description="Compatible brand slug"),
        condition: PartCondition | None = Query(None),
        kind: PartKind | None = Query(None),
        manufacturer: str | None = Query(None),
        price_min: float | None = Query(None, ge=0),
        price_max: float | None = Query(None, ge=0),
        in_stock: bool | None = Query(None),
        q: str | None = Query(None, description="Search name / article / manufacturer"),
    ) -> None:
        self.category = category
        self.brand = brand
        self.condition = condition
        self.kind = kind
        self.manufacturer = manufacturer.strip() if manufacturer and manufacturer.strip() else None
        self.price_min = price_min
        self.price_max = price_max
        self.in_stock = in_stock
        self.q = q.strip() if q and q.strip() else None

    def as_params(self) -> dict[str, object]:
        """Normalized dict for the cache key (None values dropped)."""
        out: dict[str, object] = {}
        for key, value in self.__dict__.items():
            if value is None:
                continue
            out[key] = value.value if isinstance(value, (PartCondition, PartKind)) else value
        return out


def _apply_filters(stmt: Select, f: PartFilters) -> Select:
    """Add WHERE clauses for the given filters."""
    stmt = stmt.where(Part.is_public)
    if f.category is not None:
        stmt = stmt.where(
            Part.category_id.in_(
                select(PartCategory.id).where(PartCategory.slug == f.category)
            )
        )
    if f.brand is not None:
        stmt = stmt.where(
            Part.brand_id.in_(select(Brand.id).where(Brand.slug == f.brand))
        )
    if f.condition is not None:
        stmt = stmt.where(Part.condition == f.condition)
    if f.kind is not None:
        stmt = stmt.where(Part.kind == f.kind)
    if f.manufacturer is not None:
        stmt = stmt.where(Part.manufacturer == f.manufacturer)
    if f.price_min is not None:
        stmt = stmt.where(Part.price >= f.price_min)
    if f.price_max is not None:
        stmt = stmt.where(Part.price <= f.price_max)
    if f.in_stock is not None:
        stmt = stmt.where(Part.in_stock.is_(f.in_stock))
    if f.q:
        like = f"%{f.q}%"
        stmt = stmt.where(
            or_(
                Part.name.ilike(like),
                Part.part_number.ilike(like),
                Part.manufacturer.ilike(like),
            )
        )
    return stmt


_SORT = {
    PartSort.newest: (Part.created_at.desc(), Part.id.desc()),
    PartSort.price_asc: (Part.price.asc(), Part.id.asc()),
    PartSort.price_desc: (Part.price.desc(), Part.id.desc()),
}

_LIST_LOADERS = (
    joinedload(Part.category),
    joinedload(Part.brand),
    selectinload(Part.images),
)


def _main_url(part: Part) -> str | None:
    if part.card_image_url:
        return public_url(part.card_image_url)
    if not part.images:
        return None
    main = next((i for i in part.images if i.is_main), None)
    img = main or min(part.images, key=lambda i: (i.sort_order, i.id))
    return public_url(img.url)


def _to_item(part: Part) -> PartListItem:
    return PartListItem(
        id=part.id,
        slug=part.slug,
        name=part.name,
        condition=part.condition,
        kind=part.kind,
        category=part.category.name if part.category else None,
        category_slug=part.category.slug if part.category else None,
        brand=part.brand.name if part.brand else None,
        brand_slug=part.brand.slug if part.brand else None,
        manufacturer=part.manufacturer,
        part_number=part.part_number,
        price=part.price,
        price_old=part.price_old,
        benefit_badge=part.benefit_badge,
        status_text=part.status_text,
        in_stock=part.in_stock,
        qty=part.qty,
        image_url=_main_url(part),
    )


@router.get("", response_model=PartListResponse)
async def list_parts(
    filters: PartFilters = Depends(),
    sort: PartSort = Query(PartSort.newest),
    page: int = Query(1, ge=1),
    page_size: int = Query(12, ge=1, le=60),
    session: AsyncSession = Depends(get_session),
) -> PartListResponse:
    redis = get_redis()
    version = await get_catalog_version(redis)
    key = make_key(
        version,
        "parts:list",
        {**filters.as_params(), "sort": sort.value, "page": page, "page_size": page_size},
    )
    cached = await cache_get_json(redis, key)
    if cached is not None:
        return PartListResponse.model_validate(cached)

    base = _apply_filters(select(Part), filters)
    total = await session.scalar(
        select(func.count()).select_from(base.order_by(None).subquery())
    )

    stmt = (
        base.order_by(*_SORT[sort])
        .offset((page - 1) * page_size)
        .limit(page_size)
        .options(*_LIST_LOADERS)
    )
    parts = (await session.execute(stmt)).unique().scalars().all()

    response = PartListResponse(
        items=[_to_item(p) for p in parts],
        total=total or 0,
        page=page,
        page_size=page_size,
        pages=((total or 0) + page_size - 1) // page_size,
    )
    await cache_set_json(redis, key, response.model_dump(mode="json"))
    return response


@router.get("/count", response_model=PartCountResponse)
async def count_parts(
    filters: PartFilters = Depends(),
    session: AsyncSession = Depends(get_session),
) -> PartCountResponse:
    """«Найдено N» counter for the quick-pick block."""
    redis = get_redis()
    version = await get_catalog_version(redis)
    key = make_key(version, "parts:count", filters.as_params())
    cached = await cache_get_json(redis, key)
    if cached is not None:
        return PartCountResponse.model_validate(cached)

    base = _apply_filters(select(Part), filters)
    total = await session.scalar(
        select(func.count()).select_from(base.order_by(None).subquery())
    )
    response = PartCountResponse(count=total or 0)
    await cache_set_json(redis, key, response.model_dump(mode="json"))
    return response


@router.get("/filters", response_model=PartFiltersResponse)
async def part_filters(session: AsyncSession = Depends(get_session)) -> PartFiltersResponse:
    """Filter options for the parts page. Cached, invalidated by catalog version."""
    redis = get_redis()
    version = await get_catalog_version(redis)
    key = make_key(version, "parts:filters", {})
    cached = await cache_get_json(redis, key)
    if cached is not None:
        return PartFiltersResponse.model_validate(cached)

    categories = (
        await session.execute(select(PartCategory).order_by(PartCategory.name))
    ).scalars().all()
    # Only brands that actually have at least one visible part are worth offering.
    brands = (
        await session.execute(
            select(Brand)
            .where(Brand.id.in_(select(Part.brand_id).where(Part.is_public)))
            .order_by(Brand.name)
        )
    ).scalars().all()
    manufacturers = (
        await session.execute(
            select(Part.manufacturer)
            .where(Part.is_public, Part.manufacturer.is_not(None))
            .distinct()
            .order_by(Part.manufacturer)
        )
    ).scalars().all()

    response = PartFiltersResponse(
        categories=[PartRefOption(slug=c.slug, name=c.name) for c in categories],
        brands=[
            PartBrandOption(slug=b.slug, name=b.name, logo_url=public_url(b.logo_url))
            for b in brands
        ],
        manufacturers=list(manufacturers),
        conditions=[
            PartEnumOption(value=c.value, name=_CONDITION_LABELS[c]) for c in PartCondition
        ],
        kinds=[PartEnumOption(value=k.value, name=_KIND_LABELS[k]) for k in PartKind],
    )
    await cache_set_json(redis, key, response.model_dump(mode="json"))
    return response


async def _similar_parts(session: AsyncSession, part: Part) -> list[PartListItem]:
    """Other parts, same category first, then closest by price."""
    same_category = (
        Part.category_id == part.category_id
        if part.category_id is not None
        else literal(False)
    )
    stmt = (
        select(Part)
        .where(Part.id != part.id, Part.is_public)
        .order_by(
            case((same_category, 0), else_=1),
            func.abs(Part.price - part.price),
            Part.id,
        )
        .limit(SIMILAR_LIMIT)
        .options(*_LIST_LOADERS)
    )
    rows = (await session.execute(stmt)).unique().scalars().all()
    return [_to_item(p) for p in rows]


# NOTE: this catch-all `/{slug}` route must stay declared *after* `/count` and
# `/filters` — FastAPI matches in declaration order.
@router.get("/{slug}", response_model=PartDetail)
async def get_part(
    slug: str,
    session: AsyncSession = Depends(get_session),
) -> PartDetail:
    """Detail card with gallery, specs and similar parts."""
    redis = get_redis()
    version = await get_catalog_version(redis)
    key = make_key(version, "parts:detail", {"slug": slug})
    cached = await cache_get_json(redis, key)
    if cached is not None:
        return PartDetail.model_validate(cached)

    stmt = (
        select(Part)
        .where(Part.slug == slug, Part.is_public)
        .options(*_LIST_LOADERS)
    )
    part = (await session.execute(stmt)).unique().scalar_one_or_none()
    if part is None:
        raise HTTPException(status_code=404, detail="Part not found")

    images = sorted(part.images, key=lambda i: (not i.is_main, i.sort_order, i.id))
    similar = await _similar_parts(session, part)

    item = _to_item(part).model_dump()
    detail = PartDetail(
        **item,
        description=part.description,
        images=[
            PartImageOut(url=public_url(im.url), is_main=im.is_main, sort_order=im.sort_order)
            for im in images
        ],
        similar=similar,
    )
    await cache_set_json(redis, key, detail.model_dump(mode="json"))
    return detail
