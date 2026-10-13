from __future__ import annotations

from decimal import Decimal

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

import app.api.parts as parts_api
import app.models  # noqa: F401
from app.db.base import Base
from app.db.deps import get_session
from app.main import app
from app.models.catalog import Brand
from app.models.parts import Part, PartCategory, PartCondition, PartImage, PartKind


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
    monkeypatch.setattr(parts_api, "get_redis", lambda: FakeRedis())
    monkeypatch.setattr(parts_api, "get_catalog_version", _version)
    monkeypatch.setattr(parts_api, "cache_get_json", _cache_get)
    monkeypatch.setattr(parts_api, "cache_set_json", _cache_set)

    yield factory

    app.dependency_overrides.clear()
    await engine.dispose()


async def _seed_parts(factory):
    """A brand, two categories and four parts (one hidden) for filter coverage."""
    async with factory() as session:
        zeekr = Brand(name="Zeekr", slug="zeekr", logo_url=None)
        brakes = PartCategory(name="Тормоза", slug="brakes")
        optics = PartCategory(name="Оптика", slug="optics")
        session.add_all([zeekr, brakes, optics])
        await session.flush()

        pads = Part(
            slug="brake-pads",
            name="Тормозные колодки",
            category_id=brakes.id,
            brand_id=zeekr.id,
            condition=PartCondition.new,
            kind=PartKind.original,
            manufacturer="Zeekr",
            part_number="ZK-BP-1",
            price=Decimal("18500"),
        )
        pads.images = [PartImage(url="parts/brake-pads/main.svg", is_main=True, sort_order=0)]
        disc = Part(
            slug="brake-disc",
            name="Тормозной диск",
            category_id=brakes.id,
            brand_id=zeekr.id,
            condition=PartCondition.used,
            kind=PartKind.aftermarket,
            manufacturer="Brembo",
            part_number="BR-09",
            price=Decimal("22000"),
        )
        headlight = Part(
            slug="headlight",
            name="Фара LED",
            category_id=optics.id,
            brand_id=zeekr.id,
            condition=PartCondition.new,
            kind=PartKind.original,
            manufacturer="Zeekr",
            part_number="ZK-HL-1",
            price=Decimal("89000"),
        )
        hidden = Part(
            slug="hidden-part",
            name="Скрытая запчасть",
            category_id=brakes.id,
            brand_id=zeekr.id,
            condition=PartCondition.new,
            kind=PartKind.original,
            price=Decimal("1000"),
            is_hidden=True,
        )
        session.add_all([pads, disc, headlight, hidden])
        await session.commit()


@pytest.mark.asyncio
async def test_list_and_count_only_visible(session_factory):
    await _seed_parts(session_factory)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        listing = await client.get("/parts")
        count = await client.get("/parts/count")

    slugs = {item["slug"] for item in listing.json()["items"]}
    assert slugs == {"brake-pads", "brake-disc", "headlight"}
    assert listing.json()["total"] == 3
    assert count.json()["count"] == 3


@pytest.mark.asyncio
async def test_filter_by_category(session_factory):
    await _seed_parts(session_factory)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        brakes = await client.get("/parts", params={"category": "brakes"})
        optics = await client.get("/parts", params={"category": "optics"})

    assert {i["slug"] for i in brakes.json()["items"]} == {"brake-pads", "brake-disc"}
    assert [i["slug"] for i in optics.json()["items"]] == ["headlight"]


@pytest.mark.asyncio
async def test_filter_by_condition_kind_and_price(session_factory):
    await _seed_parts(session_factory)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        used = await client.get("/parts", params={"condition": "used"})
        aftermarket = await client.get("/parts", params={"kind": "aftermarket"})
        pricey = await client.get("/parts", params={"price_min": 50000})

    assert [i["slug"] for i in used.json()["items"]] == ["brake-disc"]
    assert [i["slug"] for i in aftermarket.json()["items"]] == ["brake-disc"]
    assert [i["slug"] for i in pricey.json()["items"]] == ["headlight"]


@pytest.mark.asyncio
async def test_search_q_matches_name_article_or_manufacturer(session_factory):
    await _seed_parts(session_factory)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # SQLite LIKE only case-folds ASCII, so the Cyrillic term matches the
        # stored case; the ASCII manufacturer term still checks case-insensitivity.
        by_name = await client.get("/parts", params={"q": "Фара"})
        by_manuf = await client.get("/parts", params={"q": "brembo"})
        by_article = await client.get("/parts", params={"q": "ZK-BP"})
        none = await client.get("/parts", params={"q": "zzznope"})

    assert [i["slug"] for i in by_name.json()["items"]] == ["headlight"]
    assert [i["slug"] for i in by_manuf.json()["items"]] == ["brake-disc"]
    assert [i["slug"] for i in by_article.json()["items"]] == ["brake-pads"]
    assert none.json()["total"] == 0


@pytest.mark.asyncio
async def test_filters_endpoint_returns_options(session_factory):
    await _seed_parts(session_factory)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/parts/filters")

    data = resp.json()
    assert {c["slug"] for c in data["categories"]} == {"brakes", "optics"}
    assert [b["slug"] for b in data["brands"]] == ["zeekr"]
    assert set(data["manufacturers"]) == {"Zeekr", "Brembo"}
    assert {c["value"] for c in data["conditions"]} == {"new", "used"}
    assert {k["value"] for k in data["kinds"]} == {"original", "aftermarket"}


@pytest.mark.asyncio
async def test_detail_and_similar_are_parts_same_category_first(session_factory):
    await _seed_parts(session_factory)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        ok = await client.get("/parts/brake-pads")
        hidden = await client.get("/parts/hidden-part")

    assert hidden.status_code == 404
    assert ok.status_code == 200
    body = ok.json()
    assert body["name"] == "Тормозные колодки"
    assert body["image_url"] is not None
    # Similar must be parts; same category (brakes) ranks first, hidden excluded.
    similar_slugs = [i["slug"] for i in body["similar"]]
    assert "hidden-part" not in similar_slugs
    assert similar_slugs[0] == "brake-disc"
