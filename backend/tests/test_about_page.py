from __future__ import annotations

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

import app.models  # noqa: F401
from app.db.base import Base
from app.db.deps import get_session
from app.main import app
from app.models.home import AboutSalonPhoto, BankPartner, HomeAbout


@pytest_asyncio.fixture
async def client_and_session():
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

    app.dependency_overrides[get_session] = _override_session
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client, factory

    app.dependency_overrides.clear()
    await engine.dispose()


@pytest.mark.asyncio
async def test_about_page_returns_active_content_sorted(client_and_session):
    client, factory = client_and_session
    async with factory() as session:
        session.add(
            HomeAbout(
                description="Коротко о компании",
                page_text="Первый абзац.\n\n• Первый пункт\n• Второй пункт",
                video_url=None,
                is_active=True,
            )
        )
        session.add_all(
            [
                AboutSalonPhoto(image_url="/photo-2.jpg", alt="Второе", is_active=True, sort_order=2),
                AboutSalonPhoto(image_url="/photo-1.jpg", alt="Первое", is_active=True, sort_order=1),
                AboutSalonPhoto(image_url="/hidden.jpg", alt="Скрыто", is_active=False, sort_order=0),
                BankPartner(name="ВТБ", logo_url="/vtb.svg", is_active=True, sort_order=2),
                BankPartner(name="СБЕР БАНК", logo_url="/sber.svg", is_active=True, sort_order=1),
                BankPartner(name="Скрытый банк", logo_url="/hidden.svg", is_active=False, sort_order=0),
            ]
        )
        await session.commit()

    response = await client.get("/home/about")

    assert response.status_code == 200
    data = response.json()
    assert data["description"] == "Коротко о компании"
    assert data["page_text"].startswith("Первый абзац")
    assert [item["alt"] for item in data["photos"]] == ["Первое", "Второе"]
    assert [item["name"] for item in data["banks"]] == ["СБЕР БАНК", "ВТБ"]
