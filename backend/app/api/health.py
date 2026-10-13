"""Health and readiness probes."""
from __future__ import annotations

import redis.asyncio as aioredis
from fastapi import APIRouter
from fastapi.responses import JSONResponse

from app.core.config import get_settings
from app.db.session import ping_db

router = APIRouter(tags=["health"])


@router.get("/health")
async def health() -> dict[str, str]:
    """Liveness: process is up. No external dependencies."""
    return {"status": "ok"}


@router.get("/health/ready")
async def ready() -> JSONResponse:
    """Readiness: database and Redis are reachable."""
    settings = get_settings()
    checks: dict[str, str] = {}

    try:
        await ping_db()
        checks["db"] = "ok"
    except Exception as exc:  # noqa: BLE001 - report any failure to the probe
        checks["db"] = f"error: {exc}"

    client = aioredis.from_url(settings.redis_url)
    try:
        await client.ping()
        checks["redis"] = "ok"
    except Exception as exc:  # noqa: BLE001
        checks["redis"] = f"error: {exc}"
    finally:
        await client.aclose()

    healthy = all(v == "ok" for v in checks.values())
    return JSONResponse(
        status_code=200 if healthy else 503,
        content={"status": "ok" if healthy else "unavailable", "checks": checks},
    )
