"""Public catalog API: filtered, paginated, Redis-cached car listings.

Note: this module intentionally does *not* use ``from __future__ import
annotations`` — FastAPI must resolve the real types of the class-based query
params (``Condition``, etc.) at startup, which stringized annotations break.
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import Select, case, exists, func, literal, or_, select
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
from app.models.catalog import (
    Brand,
    Car,
    Color,
    Condition,
    Drive,
    FeatureBlock,
    Model,
    Transmission,
    Trim,
    car_color,
)
from app.schemas.catalog import (
    CarDetail,
    CarListItem,
    CarListResponse,
    CarSort,
    BenefitOut,
    ColorOut,
    CountResponse,
    FeatureGroup,
    ImageOut,
    TrimOut,
)

# How many "similar" offers to attach to a car detail.
SIMILAR_LIMIT = 4
# Stable display order for the spec feature blocks.
_FEATURE_ORDER = [FeatureBlock.safety, FeatureBlock.exterior, FeatureBlock.interior]

router = APIRouter(prefix="/cars", tags=["catalog"])


class CatalogFilters:
    """Shared query parameters for catalog listing and counting."""

    def __init__(
        self,
        brand: str | None = Query(None, description="Brand slug"),
        model: str | None = Query(None, description="Model slug"),
        body_type: str | None = Query(None, description="Body type slug"),
        transmission: str | None = Query(None, description="Transmission slug"),
        drive: str | None = Query(None, description="Drive slug"),
        engine_type: str | None = Query(None, description="Engine type slug"),
        condition: Condition | None = Query(None),
        q: str | None = Query(None, description="Free-text search by brand/model"),
        year_min: int | None = Query(None, ge=1900),
        year_max: int | None = Query(None, ge=1900),
        price_min: float | None = Query(None, ge=0),
        price_max: float | None = Query(None, ge=0),
        mileage_max: int | None = Query(None, ge=0, description="Used cars"),
    ) -> None:
        self.brand = brand
        self.model = model
        self.body_type = body_type
        self.transmission = transmission
        self.drive = drive
        self.engine_type = engine_type
        self.condition = condition
        self.q = q.strip() if q and q.strip() else None
        self.year_min = year_min
        self.year_max = year_max
        self.price_min = price_min
        self.price_max = price_max
        self.mileage_max = mileage_max

    def as_params(self) -> dict[str, object]:
        """Normalized dict for the cache key (None values dropped)."""
        return {k: v for k, v in self.__dict__.items() if v is not None}


def _apply_filters(stmt: Select, f: CatalogFilters) -> Select:
    """Add WHERE clauses for the given filters (no joins — keeps loaders clean)."""
    # Visibility gate: admin-hidden cars never reach the public API.
    stmt = stmt.where(Car.is_public)
    if f.brand is not None:
        stmt = stmt.where(
            Car.model_id.in_(
                select(Model.id).join(Brand, Model.brand_id == Brand.id).where(
                    Brand.slug == f.brand
                )
            )
        )
    if f.model is not None:
        stmt = stmt.where(
            Car.model_id.in_(select(Model.id).where(Model.slug == f.model))
        )
    if f.body_type is not None:
        from app.models.catalog import BodyType

        stmt = stmt.where(
            Car.body_type_id.in_(
                select(BodyType.id).where(BodyType.slug == f.body_type)
            )
        )
    if f.engine_type is not None:
        from app.models.catalog import EngineType

        stmt = stmt.where(
            Car.engine_type_id.in_(
                select(EngineType.id).where(EngineType.slug == f.engine_type)
            )
        )
    # transmission/drive live on Trim; each is an independent EXISTS, so a car
    # matches if *some* trim has the transmission and *some* trim the drive (not
    # necessarily the same trim). Fine for the current single-brand catalog.
    if f.transmission is not None:
        transmission_ids = select(Transmission.id).where(Transmission.slug == f.transmission)
        stmt = stmt.where(
            or_(
                Car.transmission_id.in_(transmission_ids),
                exists().where(
                    Trim.car_id == Car.id,
                    Trim.transmission_id.in_(transmission_ids),
                ),
            )
        )
    if f.drive is not None:
        drive_ids = select(Drive.id).where(Drive.slug == f.drive)
        stmt = stmt.where(
            or_(
                Car.drive_id.in_(drive_ids),
                exists().where(
                    Trim.car_id == Car.id,
                    Trim.drive_id.in_(drive_ids),
                ),
            )
        )
    if f.condition is not None:
        stmt = stmt.where(Car.condition == f.condition)
    if f.q:
        like = f"%{f.q}%"
        stmt = stmt.where(
            Car.model_id.in_(
                select(Model.id)
                .join(Brand, Model.brand_id == Brand.id)
                .where(or_(Model.name.ilike(like), Brand.name.ilike(like)))
            )
        )
    if f.year_min is not None:
        stmt = stmt.where(Car.year >= f.year_min)
    if f.year_max is not None:
        stmt = stmt.where(Car.year <= f.year_max)
    if f.price_min is not None:
        stmt = stmt.where(Car.price >= f.price_min)
    if f.price_max is not None:
        stmt = stmt.where(Car.price <= f.price_max)
    if f.mileage_max is not None:
        stmt = stmt.where(Car.mileage <= f.mileage_max)
    return stmt


_SORT = {
    CarSort.newest: (Car.created_at.desc(), Car.id.desc()),
    CarSort.price_asc: (Car.price.asc(), Car.id.asc()),
    CarSort.price_desc: (Car.price.desc(), Car.id.desc()),
    CarSort.year_desc: (Car.year.desc().nullslast(), Car.id.desc()),
}


def _gallery_main_url(car: Car) -> str | None:
    if not car.images:
        return None
    main = next((i for i in car.images if i.is_main), None)
    # Stable fallback when no main image: lowest sort_order, id as tiebreaker.
    img = main or min(car.images, key=lambda i: (i.sort_order, i.id))
    return public_url(img.url)


def _card_url(car: Car) -> str | None:
    """Catalog-grid image: the dedicated card photo, else the gallery main."""
    if car.card_image_url:
        return public_url(car.card_image_url)
    return _gallery_main_url(car)


def _to_item(car: Car) -> CarListItem:
    return CarListItem(
        id=car.id,
        slug=car.slug,
        condition=car.condition,
        brand=car.model.brand.name,
        brand_slug=car.model.brand.slug,
        model=car.model.name,
        model_slug=car.model.slug,
        title=f"{car.model.brand.name} {car.model.name}",
        price=car.price,
        price_old=car.price_old,
        benefit_badge=car.benefit_badge,
        status_text=car.status_text,
        power_hp=car.power_hp,
        fuel_consumption=car.fuel_consumption,
        fuel_consumption_petrol=car.fuel_consumption_petrol,
        acceleration_0_100=car.acceleration_0_100,
        max_speed=car.max_speed,
        year=car.year,
        mileage=car.mileage,
        engine_volume=car.engine_volume,
        body_type=car.body_type.name if car.body_type else None,
        engine_type=car.engine_type.name if car.engine_type else None,
        drive=car.drive.name if car.drive else None,
        transmission=car.transmission.name if car.transmission else None,
        in_stock=car.in_stock,
        qty=car.qty,
        is_promo=car.is_promo,
        image_url=_card_url(car),
        colors=[ColorOut.model_validate(c) for c in car.colors],
    )


@router.get("", response_model=CarListResponse)
async def list_cars(
    filters: CatalogFilters = Depends(),
    sort: CarSort = Query(CarSort.newest),
    page: int = Query(1, ge=1),
    page_size: int = Query(12, ge=1, le=60),
    session: AsyncSession = Depends(get_session),
) -> CarListResponse:
    redis = get_redis()
    version = await get_catalog_version(redis)
    key = make_key(
        version,
        "cars:list",
        {**filters.as_params(), "sort": sort.value, "page": page, "page_size": page_size},
    )
    cached = await cache_get_json(redis, key)
    if cached is not None:
        return CarListResponse.model_validate(cached)

    base = _apply_filters(select(Car), filters)
    total = await session.scalar(
        select(func.count()).select_from(base.order_by(None).subquery())
    )

    stmt = (
        base.order_by(*_SORT[sort])
        .offset((page - 1) * page_size)
        .limit(page_size)
        .options(
            joinedload(Car.model).joinedload(Model.brand),
            joinedload(Car.body_type),
            joinedload(Car.engine_type),
            joinedload(Car.drive),
            joinedload(Car.transmission),
            selectinload(Car.colors),
            selectinload(Car.images),
        )
    )
    cars = (await session.execute(stmt)).unique().scalars().all()

    response = CarListResponse(
        items=[_to_item(c) for c in cars],
        total=total or 0,
        page=page,
        page_size=page_size,
        pages=((total or 0) + page_size - 1) // page_size,
    )
    await cache_set_json(redis, key, response.model_dump(mode="json"))
    return response


@router.get("/count", response_model=CountResponse)
async def count_cars(
    filters: CatalogFilters = Depends(),
    session: AsyncSession = Depends(get_session),
) -> CountResponse:
    """«Найдено N» counter for the quick-pick block."""
    redis = get_redis()
    version = await get_catalog_version(redis)
    key = make_key(version, "cars:count", filters.as_params())
    cached = await cache_get_json(redis, key)
    if cached is not None:
        return CountResponse.model_validate(cached)

    base = _apply_filters(select(Car), filters)
    total = await session.scalar(
        select(func.count()).select_from(base.order_by(None).subquery())
    )
    response = CountResponse(count=total or 0)
    await cache_set_json(redis, key, response.model_dump(mode="json"))
    return response


async def _similar_cars(session: AsyncSession, car: Car) -> list[CarListItem]:
    """Other cars, same body type first, then closest by price.

    If the car has no body type, ``same_body`` is a constant false, so results
    fall back to pure price proximity — intentional, not an oversight.
    """
    same_body = (
        Car.body_type_id == car.body_type_id
        if car.body_type_id is not None
        else literal(False)
    )
    stmt = (
        select(Car)
        .where(Car.id != car.id, Car.is_public)
        .order_by(
            case((same_body, 0), else_=1),
            func.abs(Car.price - car.price),
            Car.id,
        )
        .limit(SIMILAR_LIMIT)
        .options(
            joinedload(Car.model).joinedload(Model.brand),
            joinedload(Car.body_type),
            joinedload(Car.engine_type),
            joinedload(Car.drive),
            joinedload(Car.transmission),
            selectinload(Car.colors),
            selectinload(Car.images),
        )
    )
    rows = (await session.execute(stmt)).unique().scalars().all()
    return [_to_item(c) for c in rows]


def _to_detail(
    car: Car, similar: list[CarListItem], colors_out: list[ColorOut]
) -> CarDetail:
    images = sorted(car.images, key=lambda i: (not i.is_main, i.sort_order, i.id))
    trims = sorted(car.trims, key=lambda t: (t.sort_order, t.id))

    by_block: dict[FeatureBlock, list] = {}
    for feat in car.features:
        by_block.setdefault(feat.block, []).append(feat)
    features = [
        FeatureGroup(
            block=block.value,
            items=[
                f.text for f in sorted(by_block[block], key=lambda x: (x.sort_order, x.id))
            ],
        )
        for block in _FEATURE_ORDER
        if by_block.get(block)
    ]
    gifts = [g.text for g in sorted(car.gifts, key=lambda g: (g.sort_order, g.id))]
    benefits = [
        BenefitOut(icon=b.icon, text=b.text, sort_order=b.sort_order)
        for b in sorted(
            (b for b in car.benefits if b.is_active),
            key=lambda b: (b.sort_order, b.id),
        )
    ]

    item = _to_item(car).model_dump()
    item["colors"] = [c.model_dump() for c in colors_out]
    return CarDetail(
        **item,
        images=[
            ImageOut(url=public_url(im.url), is_main=im.is_main, sort_order=im.sort_order)
            for im in images
        ],
        trims=[
            TrimOut(
                id=t.id,
                name=t.name,
                engine_volume=t.engine_volume,
                power_hp=t.power_hp,
                transmission=t.transmission.name if t.transmission else None,
                drive=t.drive.name if t.drive else None,
                price=t.price,
                price_discount=t.price_discount,
                sort_order=t.sort_order,
                image_url=public_url(t.image_url) if t.image_url else None,
            )
            for t in trims
        ],
        benefits=benefits,
        features=features,
        gifts=gifts,
        similar=similar,
    )


# NOTE: this catch-all `/{slug}` route must stay declared *after* `/count`
# (and any other static sub-paths) — FastAPI matches in declaration order.
@router.get("/{slug}", response_model=CarDetail)
async def get_car(
    slug: str,
    session: AsyncSession = Depends(get_session),
) -> CarDetail:
    """Detail card with gallery, trims, specs, colors and similar offers."""
    redis = get_redis()
    version = await get_catalog_version(redis)
    key = make_key(version, "cars:detail", {"slug": slug})
    cached = await cache_get_json(redis, key)
    if cached is not None:
        return CarDetail.model_validate(cached)

    stmt = (
        select(Car)
        .where(Car.slug == slug, Car.is_public)
        .options(
            joinedload(Car.model).joinedload(Model.brand),
            joinedload(Car.body_type),
            joinedload(Car.engine_type),
            joinedload(Car.drive),
            joinedload(Car.transmission),
            selectinload(Car.colors),
            selectinload(Car.images),
            selectinload(Car.trims).joinedload(Trim.transmission),
            selectinload(Car.trims).joinedload(Trim.drive),
            selectinload(Car.benefits),
            selectinload(Car.features),
            selectinload(Car.gifts),
        )
    )
    car = (await session.execute(stmt)).unique().scalar_one_or_none()
    if car is None:
        raise HTTPException(status_code=404, detail="Car not found")

    # Per-colour hero banners (1 colour = 1 picture), ordered for a stable swatch row.
    color_rows = (
        await session.execute(
            select(Color.name, Color.hex, car_color.c.image_url)
            .join(car_color, car_color.c.color_id == Color.id)
            .where(car_color.c.car_id == car.id)
            .order_by(Color.name)
        )
    ).all()
    colors_out = [
        ColorOut(name=name, hex=hex_, image_url=public_url(img) if img else None)
        for name, hex_, img in color_rows
    ]

    similar = await _similar_cars(session, car)
    detail = _to_detail(car, similar, colors_out)
    await cache_set_json(redis, key, detail.model_dump(mode="json"))
    return detail
