"""Catalog metadata: filter options for the «Я ищу» block and brand sidebar."""
from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

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
    BodyType,
    Brand,
    Drive,
    EngineType,
    Model,
    Transmission,
)
from app.schemas.catalog import (
    BrandOption,
    FiltersResponse,
    ModelOption,
    RefOption,
)

router = APIRouter(prefix="/catalog", tags=["catalog"])


async def _ref_options(session: AsyncSession, model) -> list[RefOption]:
    rows = (await session.execute(select(model).order_by(model.name))).scalars().all()
    return [RefOption(slug=r.slug, name=r.name) for r in rows]


@router.get("/filters", response_model=FiltersResponse)
async def filters(session: AsyncSession = Depends(get_session)) -> FiltersResponse:
    """Filter options in one response. Cached, invalidated by catalog version."""
    redis = get_redis()
    version = await get_catalog_version(redis)
    key = make_key(version, "catalog:filters", {})
    cached = await cache_get_json(redis, key)
    if cached is not None:
        return FiltersResponse.model_validate(cached)

    brands = (await session.execute(select(Brand).order_by(Brand.name))).scalars().all()
    models = (
        await session.execute(
            select(Model).options(joinedload(Model.brand)).order_by(Model.name)
        )
    ).scalars().all()

    response = FiltersResponse(
        brands=[
            BrandOption(slug=b.slug, name=b.name, logo_url=public_url(b.logo_url))
            for b in brands
        ],
        models=[
            ModelOption(slug=m.slug, name=m.name, brand_slug=m.brand.slug) for m in models
        ],
        body_types=await _ref_options(session, BodyType),
        transmissions=await _ref_options(session, Transmission),
        drives=await _ref_options(session, Drive),
        engine_types=await _ref_options(session, EngineType),
    )
    await cache_set_json(redis, key, response.model_dump(mode="json"))
    return response
