from __future__ import annotations

from decimal import Decimal

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

import app.api.catalog as catalog_api
import app.models  # noqa: F401
from app.db.base import Base
from app.db.deps import get_session
from app.main import app
from app.models.catalog import Brand, Car, Condition, Drive, Model, Transmission


class FakeRedis:
    async def get(self, _key):
        return None

    async def set(self, *_args, **_kwargs):
        return None

    async def incr(self, _key):
        return 2


@pytest_asyncio.fixture
async def session_factory(monkeypatch):
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)

    async def _override_session():
        async with factory() as session:
            yield session

    async def _version(_redis):
        return 1

    async def _cache_get(*_args, **_kwargs):
        return None

    async def _cache_set(*_args, **_kwargs):
        return None

    app.dependency_overrides[get_session] = _override_session
    monkeypatch.setattr(catalog_api, "get_redis", lambda: FakeRedis())
    monkeypatch.setattr(catalog_api, "get_catalog_version", _version)
    monkeypatch.setattr(catalog_api, "cache_get_json", _cache_get)
    monkeypatch.setattr(catalog_api, "cache_set_json", _cache_set)

    yield factory

    app.dependency_overrides.clear()
    await engine.dispose()


async def _seed_cars(factory):
    """A visible and a hidden car on the same brand/model for a clean compare."""
    async with factory() as session:
        brand = Brand(name="Zeekr", slug="zeekr", logo_url=None)
        model = Model(name="9X", slug="9x", brand=brand)
        session.add_all([brand, model])
        await session.flush()
        for slug, is_hidden in (
            ("zeekr-visible", False),
            ("zeekr-hidden", True),
        ):
            session.add(
                Car(
                    slug=slug,
                    condition=Condition.new,
                    model_id=model.id,
                    price=Decimal("9900000"),
                    is_hidden=is_hidden,
                )
            )
        await session.commit()


@pytest.mark.asyncio
async def test_list_and_count_only_visible(session_factory):
    await _seed_cars(session_factory)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        listing = await client.get("/cars")
        count = await client.get("/cars/count")

    slugs = [item["slug"] for item in listing.json()["items"]]
    assert slugs == ["zeekr-visible"]
    assert listing.json()["total"] == 1
    assert count.json()["count"] == 1


@pytest.mark.asyncio
async def test_detail_404_for_hidden(session_factory):
    await _seed_cars(session_factory)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        ok = await client.get("/cars/zeekr-visible")
        hidden = await client.get("/cars/zeekr-hidden")

    assert ok.status_code == 200
    assert hidden.status_code == 404


@pytest.mark.asyncio
async def test_similar_excludes_hidden(session_factory):
    await _seed_cars(session_factory)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        detail = await client.get("/cars/zeekr-visible")

    # The only other car is hidden, so there are no similar offers.
    assert detail.json()["similar"] == []


@pytest.mark.asyncio
async def test_used_car_filters_match_car_level_drive_and_transmission(session_factory):
    async with session_factory() as session:
        brand = Brand(name="Zeekr", slug="zeekr", logo_url=None)
        model = Model(name="009", slug="009", brand=brand)
        transmission = Transmission(name="Автомат", slug="avtomat")
        drive = Drive(name="Полный", slug="full")
        car = Car(
            slug="zeekr-009-used",
            condition=Condition.used,
            model=model,
            transmission=transmission,
            drive=drive,
            price=Decimal("20500000"),
            year=2025,
            mileage=12000,
        )
        session.add_all([brand, model, transmission, drive, car])
        await session.commit()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get(
            "/cars",
            params={
                "condition": "used",
                "transmission": "avtomat",
                "drive": "full",
                "price_min": 20000000,
            },
        )

    assert response.status_code == 200
    assert [item["slug"] for item in response.json()["items"]] == ["zeekr-009-used"]


@pytest.mark.asyncio
async def test_search_q_matches_brand_or_model_name(session_factory):
    """`q` does a case-insensitive match on brand and model names."""
    async with session_factory() as session:
        zeekr = Brand(name="Zeekr", slug="zeekr", logo_url=None)
        skoda = Brand(name="Skoda", slug="skoda", logo_url=None)
        zeekr_9x = Model(name="9X", slug="9x", brand=zeekr)
        skoda_octavia = Model(name="Octavia", slug="octavia", brand=skoda)
        session.add_all([zeekr, skoda, zeekr_9x, skoda_octavia])
        await session.flush()
        session.add_all(
            [
                Car(slug="zeekr-9x", condition=Condition.new, model_id=zeekr_9x.id, price=Decimal("9900000")),
                Car(slug="skoda-octavia", condition=Condition.new, model_id=skoda_octavia.id, price=Decimal("1615000")),
            ]
        )
        await session.commit()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        by_brand = await client.get("/cars", params={"q": "skoda"})
        by_model = await client.get("/cars", params={"q": "octav"})
        no_match = await client.get("/cars", params={"q": "zzznope"})

    assert [item["slug"] for item in by_brand.json()["items"]] == ["skoda-octavia"]
    assert [item["slug"] for item in by_model.json()["items"]] == ["skoda-octavia"]
    assert no_match.json()["total"] == 0
