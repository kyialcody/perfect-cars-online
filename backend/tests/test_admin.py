"""Tests for the SQLAdmin auth backend and admin bootstrap (issue #18).

These exercise the auth-critical logic directly against an in-memory SQLite
session, without standing up the full SQLAdmin HTTP stack (which is bound to
the Postgres engine at import time).
"""
from __future__ import annotations

import pytest
import pytest_asyncio
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

import app.admin as admin_pkg
import app.admin.auth as admin_auth
import app.models  # noqa: F401 - register models on Base.metadata
from app.admin import ensure_admin_user
from app.admin.auth import AdminAuth
from app.core.security import hash_password
from app.db.base import Base
from app.models.user import User


class FakeRequest:
    """Minimal stand-in for Starlette's Request used by AdminAuth."""

    def __init__(self, form: dict | None = None, session: dict | None = None) -> None:
        self._form = form or {}
        self.session = session if session is not None else {}

    async def form(self) -> dict:
        return self._form


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

    # Admin code uses SessionLocal directly (not the get_session dependency),
    # so point both modules' references at the test factory.
    monkeypatch.setattr(admin_auth, "SessionLocal", factory)
    monkeypatch.setattr(admin_pkg, "SessionLocal", factory)

    yield factory
    await engine.dispose()


async def _add_user(factory, *, email, password, is_admin=True, is_active=True):
    async with factory() as session:
        session.add(
            User(
                email=email.lower(),
                password_hash=hash_password(password),
                is_admin=is_admin,
                is_active=is_active,
            )
        )
        await session.commit()


@pytest.mark.asyncio
async def test_login_accepts_admin(session_factory):
    await _add_user(session_factory, email="admin@x.io", password="s3cret", is_admin=True)
    backend = AdminAuth(secret_key="test")
    req = FakeRequest({"username": "admin@x.io", "password": "s3cret"})
    assert await backend.login(req) is True
    assert req.session.get("admin_user_id")


@pytest.mark.asyncio
async def test_login_rejects_non_admin(session_factory):
    await _add_user(session_factory, email="user@x.io", password="s3cret", is_admin=False)
    backend = AdminAuth(secret_key="test")
    req = FakeRequest({"username": "user@x.io", "password": "s3cret"})
    assert await backend.login(req) is False
    assert "admin_user_id" not in req.session


@pytest.mark.asyncio
async def test_login_rejects_wrong_password(session_factory):
    await _add_user(session_factory, email="admin@x.io", password="s3cret", is_admin=True)
    backend = AdminAuth(secret_key="test")
    req = FakeRequest({"username": "admin@x.io", "password": "nope"})
    assert await backend.login(req) is False


@pytest.mark.asyncio
async def test_login_rejects_unknown_user(session_factory):
    backend = AdminAuth(secret_key="test")
    req = FakeRequest({"username": "ghost@x.io", "password": "whatever"})
    assert await backend.login(req) is False


@pytest.mark.asyncio
async def test_authenticate_checks_admin_each_request(session_factory):
    await _add_user(session_factory, email="admin@x.io", password="s3cret", is_admin=True)
    async with session_factory() as s:
        admin_id = (
            await s.execute(select(User.id).where(User.email == "admin@x.io"))
        ).scalar_one()

    backend = AdminAuth(secret_key="test")
    assert await backend.authenticate(FakeRequest(session={"admin_user_id": admin_id})) is True
    assert await backend.authenticate(FakeRequest(session={})) is False

    # Revoking admin rights locks the session out immediately.
    async with session_factory() as s:
        user = await s.get(User, admin_id)
        user.is_admin = False
        await s.commit()
    assert await backend.authenticate(FakeRequest(session={"admin_user_id": admin_id})) is False


@pytest.mark.asyncio
async def test_ensure_admin_user_creates_and_promotes(session_factory, monkeypatch):
    class _Settings:
        admin_email = "boss@x.io"
        admin_password = "bootstrap-pw"

    monkeypatch.setattr(admin_pkg, "get_settings", lambda: _Settings())

    # First call creates the admin.
    await ensure_admin_user()
    async with session_factory() as s:
        user = (
            await s.execute(select(User).where(func.lower(User.email) == "boss@x.io"))
        ).scalar_one()
        assert user.is_admin and user.is_active

    # Demote, then re-run: it promotes the existing account (no duplicate).
    async with session_factory() as s:
        u = await s.get(User, user.id)
        u.is_admin = False
        await s.commit()
    await ensure_admin_user()
    async with session_factory() as s:
        count = (
            await s.execute(
                select(func.count()).select_from(User).where(func.lower(User.email) == "boss@x.io")
            )
        ).scalar_one()
        promoted = (await s.get(User, user.id)).is_admin
    assert count == 1
    assert promoted is True


@pytest.mark.asyncio
async def test_ensure_admin_user_noop_without_credentials(session_factory, monkeypatch):
    class _Settings:
        admin_email = ""
        admin_password = ""

    monkeypatch.setattr(admin_pkg, "get_settings", lambda: _Settings())
    await ensure_admin_user()
    async with session_factory() as s:
        count = (await s.execute(select(func.count()).select_from(User))).scalar_one()
    assert count == 0
