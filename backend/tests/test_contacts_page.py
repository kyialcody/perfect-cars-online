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
from app.models.home import (
    ContactAddress,
    ContactInfo,
    ContactPhone,
    ContactPhoto,
    Requisite,
    SocialLink,
)


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
async def test_contacts_page_returns_active_content_sorted(client_and_session):
    client, factory = client_and_session
    async with factory() as session:
        session.add(
            ContactInfo(
                about_text="О нас коротко",
                footer_about_text="Текст футера",
                is_active=True,
            )
        )
        session.add_all(
            [
                ContactPhone(value="+7 (495) 000-00-02", is_active=True, sort_order=2),
                ContactPhone(value="+7 (800) 000-00-01", is_active=True, sort_order=1),
                ContactPhone(value="+7 (000) 000-00-00", is_active=False, sort_order=0),
                ContactAddress(value="Второй адрес", is_active=True, sort_order=2, show_in_header=False),
                ContactAddress(value="Первый адрес", is_active=True, sort_order=1, show_in_header=True),
                ContactPhoto(image_url="/c-2.jpg", alt="Второе", is_active=True, sort_order=2),
                ContactPhoto(image_url="/c-1.jpg", alt="Первое", is_active=True, sort_order=1),
                ContactPhoto(image_url="/hidden.jpg", alt="Скрыто", is_active=False, sort_order=0),
                Requisite(label="ИНН", value="123", is_active=True, sort_order=2),
                Requisite(label="ОГРН", value="456", is_active=True, sort_order=1),
                Requisite(label="Скрыто", value="x", is_active=False, sort_order=0),
                SocialLink(kind="telegram", url="https://t.me/x", is_active=True, sort_order=2),
                SocialLink(kind="phone", url="tel:+7", is_active=True, sort_order=1),
                SocialLink(kind="vk", url="#", is_active=False, sort_order=0),
            ]
        )
        await session.commit()

    response = await client.get("/home/contacts")

    assert response.status_code == 200
    data = response.json()
    assert data["about_text"] == "О нас коротко"
    assert data["footer_about_text"] == "Текст футера"
    assert [p["value"] for p in data["phones"]] == ["+7 (800) 000-00-01", "+7 (495) 000-00-02"]
    assert [a["value"] for a in data["addresses"]] == ["Первый адрес", "Второй адрес"]
    assert [a["show_in_header"] for a in data["addresses"]] == [True, False]
    assert [p["alt"] for p in data["photos"]] == ["Первое", "Второе"]
    assert [r["label"] for r in data["requisites"]] == ["ОГРН", "ИНН"]
    assert [s["kind"] for s in data["socials"]] == ["phone", "telegram"]


@pytest.mark.asyncio
async def test_contacts_page_empty(client_and_session):
    client, _ = client_and_session

    response = await client.get("/home/contacts")

    assert response.status_code == 200
    data = response.json()
    assert data == {
        "about_text": None,
        "footer_about_text": None,
        "phones": [],
        "addresses": [],
        "photos": [],
        "requisites": [],
        "socials": [],
    }
