"""Test fixtures: an in-memory SQLite DB and an ASGI client with overrides.

Tests run without Postgres or Redis — the DB session is backed by a shared
in-memory SQLite, and the login rate limiter (Redis) is stubbed to always
allow, so the suite is hermetic.
"""
from __future__ import annotations

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

import app.models  # noqa: F401 - register all models on Base.metadata
from app.db.base import Base
from app.db.deps import get_session
from app.main import app


@pytest_asyncio.fixture
async def client(monkeypatch):
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

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()
    await engine.dispose()
