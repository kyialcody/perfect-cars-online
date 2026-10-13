from __future__ import annotations

from decimal import Decimal

import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

import app.admin.parts_composer as parts_composer
import app.models  # noqa: F401
from app.db.base import Base
from app.models.catalog import Brand
from app.models.parts import Part, PartCategory, PartCondition, PartKind


class FakeForm(dict):
    def getlist(self, key):
        value = self.get(key, [])
        return value if isinstance(value, list) else [value]


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

    async def _noop(*_args, **_kwargs):
        return None

    monkeypatch.setattr(parts_composer, "SessionLocal", factory)
    monkeypatch.setattr(parts_composer, "bump_catalog_version", _noop)

    yield factory
    await engine.dispose()


async def _seed_refs(factory):
    async with factory() as session:
        brand = Brand(name="Zeekr", slug="zeekr", logo_url=None)
        category = PartCategory(name="Тормоза", slug="brakes")
        session.add_all([brand, category])
        await session.commit()
        return brand.id, category.id


@pytest.mark.asyncio
async def test_save_creates_part(session_factory):
    brand_id, category_id = await _seed_refs(session_factory)
    form = FakeForm(
        {
            "slug": "brake-pads",
            "name": "Тормозные колодки",
            "category_id": str(category_id),
            "brand_id": str(brand_id),
            "condition": "used",
            "kind": "aftermarket",
            "manufacturer": "Brembo",
            "part_number": "BR-09",
            "price": "22000",
            "price_old": "25000",
            "qty": "4",
            "in_stock": "1",
            "description": "Отличные колодки",
            "image_count": "0",
            "images": [],
        }
    )
    response = await parts_composer.save_part(form)
    assert response.status_code == 200

    async with session_factory() as session:
        part = (await session.execute(select(Part).where(Part.slug == "brake-pads"))).scalar_one()
        assert part.name == "Тормозные колодки"
        assert part.category_id == category_id
        assert part.brand_id == brand_id
        assert part.condition == PartCondition.used
        assert part.kind == PartKind.aftermarket
        assert part.price == Decimal("22000")
        assert part.qty == 4


@pytest.mark.asyncio
async def test_save_rejects_missing_name_or_slug(session_factory):
    await _seed_refs(session_factory)
    form = FakeForm({"slug": "", "name": "", "price": "1000", "image_count": "0"})
    response = await parts_composer.save_part(form)
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_save_rejects_duplicate_slug(session_factory):
    await _seed_refs(session_factory)
    base = {"name": "Деталь", "price": "1000", "image_count": "0", "images": []}
    first = await parts_composer.save_part(FakeForm({**base, "slug": "dup"}))
    assert first.status_code == 200
    second = await parts_composer.save_part(FakeForm({**base, "slug": "dup"}))
    assert second.status_code == 409


@pytest.mark.asyncio
async def test_toggle_visibility(session_factory):
    await _seed_refs(session_factory)
    await parts_composer.save_part(
        FakeForm({"slug": "p1", "name": "P1", "price": "1000", "image_count": "0", "images": []})
    )
    async with session_factory() as session:
        part_id = (await session.execute(select(Part.id).where(Part.slug == "p1"))).scalar_one()

    response = await parts_composer.toggle_visibility(FakeForm({"part_id": str(part_id)}))
    assert response.status_code == 303
    async with session_factory() as session:
        assert (await session.get(Part, part_id)).is_hidden is True
