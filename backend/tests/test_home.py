"""Tests for the homepage content API added in #80.

Covers the About block, the dealer-location pins, and the show_on_home split
between the home carousel (/home) and the catalog picks page (/home/collections).
"""
from __future__ import annotations

from decimal import Decimal

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

import app.models  # noqa: F401 - register all models on Base.metadata
from app.db.base import Base
from app.db.deps import get_session
from app.main import app
from app.models.catalog import Brand, Car, Condition, Model
from app.models.home import BankPartner, DealerLocation, HomeAbout, HomeCollection


@pytest_asyncio.fixture
async def factory():
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async def _override_session():
        async with session_factory() as session:
            yield session

    app.dependency_overrides[get_session] = _override_session
    yield session_factory
    app.dependency_overrides.clear()
    await engine.dispose()


def _client() -> AsyncClient:
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


@pytest.mark.asyncio
async def test_home_includes_active_about(factory):
    async with factory() as session:
        session.add(HomeAbout(description="Большой автосалон", video_url="https://youtu.be/abc12345678", is_active=True))
        await session.commit()

    async with _client() as client:
        body = (await client.get("/home")).json()

    assert body["about"] is not None
    assert body["about"]["description"] == "Большой автосалон"
    assert body["about"]["video_url"] == "https://youtu.be/abc12345678"


@pytest.mark.asyncio
async def test_home_about_null_when_inactive(factory):
    async with factory() as session:
        session.add(HomeAbout(description="скрыто", video_url=None, is_active=False))
        await session.commit()

    async with _client() as client:
        body = (await client.get("/home")).json()

    assert body["about"] is None


@pytest.mark.asyncio
async def test_show_on_home_splits_carousel_and_picks(factory):
    async with factory() as session:
        session.add_all([
            HomeCollection(slug="fam", title="Семейные", show_on_home=True, is_active=True),
            HomeCollection(slug="vans", title="Фургоны", show_on_home=False, is_active=True),
            HomeCollection(slug="off", title="Скрытая", show_on_home=True, is_active=False),
        ])
        await session.commit()

    async with _client() as client:
        home = (await client.get("/home")).json()
        picks = (await client.get("/home/collections")).json()

    # Carousel: only active + show_on_home
    assert {c["title"] for c in home["collections"]} == {"Семейные"}
    # Picks page: all active, regardless of show_on_home
    assert {c["title"] for c in picks} == {"Семейные", "Фургоны"}


@pytest.mark.asyncio
async def test_locations_returns_active_pins_sorted(factory):
    async with factory() as session:
        session.add_all([
            DealerLocation(
                name="Второй", address="ул. Б", lat=42.5, lng=74.6,
                phone="+7 000", hours="9-18", is_active=True, sort_order=2,
            ),
            DealerLocation(
                name="Первый", address="ул. А", lat=42.8, lng=74.6,
                is_active=True, sort_order=1,
            ),
            DealerLocation(
                name="Выключенный", address="ул. В", lat=0.0, lng=0.0,
                is_active=False, sort_order=0,
            ),
        ])
        await session.commit()

    async with _client() as client:
        rows = (await client.get("/home/locations")).json()

    assert [r["name"] for r in rows] == ["Первый", "Второй"]
    assert rows[0]["phone"] is None
    assert rows[1]["phone"] == "+7 000"


