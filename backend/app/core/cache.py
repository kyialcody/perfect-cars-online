"""Redis caching for catalog selections.

Cached responses are namespaced by a *catalog version* counter. Any change to
the catalog (admin CRUD in issue #11, or re-running the seed) calls
``bump_catalog_version`` which increments that counter, so every previously
cached key becomes unreachable at once — a cheap, race-free invalidation that
needs no key scanning.
"""
from __future__ import annotations

import hashlib
import json
from typing import Any

import redis.asyncio as aioredis

from app.core.config import get_settings

_VERSION_KEY = "catalog:version"
DEFAULT_TTL = 60  # seconds

_client: aioredis.Redis | None = None


def get_redis() -> aioredis.Redis:
    """Return a process-wide Redis client (decodes responses to str)."""
    global _client
    if _client is None:
        _client = aioredis.from_url(
            get_settings().redis_url, encoding="utf-8", decode_responses=True
        )
    return _client


async def get_catalog_version(redis: aioredis.Redis) -> int:
    """Current catalog version; initialised to 1 on first read."""
    value = await redis.get(_VERSION_KEY)
    if value is None:
        # SETNX so concurrent callers agree on the same starting version.
        await redis.set(_VERSION_KEY, 1, nx=True)
        value = await redis.get(_VERSION_KEY)
    return int(value)


async def bump_catalog_version(redis: aioredis.Redis | None = None) -> int:
    """Invalidate every cached selection by moving to a new version."""
    redis = redis or get_redis()
    return int(await redis.incr(_VERSION_KEY))


def make_key(version: int, prefix: str, params: dict[str, Any]) -> str:
    """Deterministic cache key from a version, a prefix and query params."""
    payload = json.dumps(params, sort_keys=True, ensure_ascii=False, default=str)
    digest = hashlib.sha1(payload.encode("utf-8")).hexdigest()
    return f"catalog:v{version}:{prefix}:{digest}"


async def cache_get_json(redis: aioredis.Redis, key: str) -> Any | None:
    raw = await redis.get(key)
    return json.loads(raw) if raw is not None else None


async def cache_set_json(
    redis: aioredis.Redis, key: str, value: Any, ttl: int = DEFAULT_TTL
) -> None:
    await redis.set(key, json.dumps(value, ensure_ascii=False, default=str), ex=ttl)
