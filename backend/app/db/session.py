"""Async SQLAlchemy engine and session factory.

ORM models arrive in issue #4; this module only wires the connection and
exposes a lightweight `ping_db()` used by the readiness probe.
"""
from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import get_settings

settings = get_settings()

engine = create_async_engine(settings.database_url, pool_pre_ping=True)
SessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


async def ping_db() -> None:
    """Run a trivial query; raises if the database is unreachable."""
    async with engine.connect() as conn:
        await conn.execute(text("SELECT 1"))
