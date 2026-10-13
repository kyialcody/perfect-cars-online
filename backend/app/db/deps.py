"""FastAPI dependencies for the database layer."""
from __future__ import annotations

from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import SessionLocal


async def get_session() -> AsyncIterator[AsyncSession]:
    """Yield a request-scoped async session and close it afterwards."""
    async with SessionLocal() as session:
        yield session
