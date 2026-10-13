from __future__ import annotations

from decimal import Decimal

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

import app.models  # noqa: F401
from app.db.base import Base
from app.db.deps import get_session
from app.main import app
from app.models.catalog import Brand, Car, Condition, Model

PASSWORD = "Sup3rSecret!"


@pytest_asyncio.fixture
async def factory(monkeypatch):
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

    async def _allow(*_args, **_kwargs) -> bool:
        return True

    app.dependency_overrides[get_session] = _override_session
    monkeypatch.setattr("app.api.auth.hit", _allow)
    monkeypatch.setattr("app.api.leads.hit", _allow)

    yield session_factory

    app.dependency_overrides.clear()
    await engine.dispose()


def _client() -> AsyncClient:
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


async def _register_and_login(client: AsyncClient, email: str) -> str:
    reg = await client.post(
        "/auth/register",
        json={
            "email": email,
            "password": PASSWORD,
            "full_name": "Alice",
            "phone": "+7 999 111-22-33",
        },
    )
    assert reg.status_code == 201, reg.text
    login = await client.post("/auth/login", json={"email": email, "password": PASSWORD})
    assert login.status_code == 200, login.text
    return login.json()["access_token"]


async def _car(factory) -> int:
    async with factory() as session:
        brand = Brand(name="Zeekr", slug="zeekr", logo_url=None)
        model = Model(name="001", slug="001", brand=brand)
        session.add_all([brand, model])
        await session.flush()
        car = Car(
            slug="zeekr-001",
            condition=Condition.new,
            model_id=model.id,
            price=Decimal("5500000"),
            is_hidden=False,
        )
        session.add(car)
        await session.commit()
        return car.id


@pytest.mark.asyncio
async def test_registration_accepts_phone_and_blocks_gmail(factory):
    async with _client() as client:
        gmail = await client.post(
            "/auth/register",
            json={
                "email": "user@gmail.com",
                "password": PASSWORD,
                "phone": "+7 999 111-22-33",
            },
        )
        assert gmail.status_code == 451

        ok = await client.post(
            "/auth/register",
            json={
                "email": "user@example.com",
                "password": PASSWORD,
                "phone": "89991112233",
            },
        )
        assert ok.status_code == 201, ok.text
        assert ok.json()["phone"] == "+79991112233"


@pytest.mark.asyncio
async def test_profile_password_change(factory):
    async with _client() as client:
        token = await _register_and_login(client, "alice@example.com")
        headers = {"Authorization": f"Bearer {token}"}

        mismatch = await client.post(
            "/profile/password",
            json={"current_password": "wrong", "new_password": "NewSecret123"},
            headers=headers,
        )
        assert mismatch.status_code == 400

        changed = await client.post(
            "/profile/password",
            json={"current_password": PASSWORD, "new_password": "NewSecret123"},
            headers=headers,
        )
        assert changed.status_code == 200

        old_login = await client.post(
            "/auth/login",
            json={"email": "alice@example.com", "password": PASSWORD},
        )
        assert old_login.status_code == 401
        new_login = await client.post(
            "/auth/login",
            json={"email": "alice@example.com", "password": "NewSecret123"},
        )
        assert new_login.status_code == 200


@pytest.mark.asyncio
async def test_leads_require_jwt_and_dedupe(factory):
    car_id = await _car(factory)
    payload = {
        "name": "Alice",
        "phone": "+7 999 111-22-33",
        "source": "catalog",
        "source_title": "Купить Zeekr 001",
        "dedupe_key": "purchase:1",
        "car_id": car_id,
        "consent": True,
    }

    async with _client() as client:
        assert (await client.post("/leads", json=payload)).status_code in (401, 403)
        token = await _register_and_login(client, "alice@example.com")
        headers = {"Authorization": f"Bearer {token}"}
        first = await client.post("/leads", json=payload, headers=headers)
        assert first.status_code == 201, first.text
        second = await client.post("/leads", json=payload, headers=headers)
        assert second.status_code == 201, second.text
        assert second.json()["id"] == first.json()["id"]


@pytest.mark.asyncio
async def test_profile_lists_only_own_leads(factory):
    car_id = await _car(factory)
    async with _client() as client:
        alice = await _register_and_login(client, "alice@example.com")
        bob = await _register_and_login(client, "bob@example.com")
        lead_payload = {
            "name": "Alice",
            "phone": "+7 999 111-22-33",
            "source_title": "Купить Zeekr 001",
            "dedupe_key": "purchase:1",
            "car_id": car_id,
            "consent": True,
        }
        alice_headers = {"Authorization": f"Bearer {alice}"}
        bob_headers = {"Authorization": f"Bearer {bob}"}
        lead = (await client.post("/leads", json=lead_payload, headers=alice_headers)).json()

        own = await client.get("/profile/leads", headers=alice_headers)
        other = await client.get("/profile/leads", headers=bob_headers)
        assert [item["id"] for item in own.json()] == [lead["id"]]
        assert own.json()[0]["status"] == "new"
        # A lead carries no booking/prepayment anymore.
        assert "booking" not in own.json()[0]
        assert other.json() == []
