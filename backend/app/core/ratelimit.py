"""Simple fixed-window rate limiting backed by Redis."""
from __future__ import annotations

from app.core.cache import get_redis


async def hit(key: str, limit: int, window: int) -> bool:
    """Register one hit for ``key``; return True if still within ``limit``.

    Fixed window. INCR and EXPIRE run in one pipeline (MULTI/EXEC) so they are
    atomic — a crash can't leave the key without a TTL (which would block the IP
    forever). ``EXPIRE ... NX`` only sets the TTL when the key has none, so the
    window starts on the first hit and isn't extended by later ones.
    """
    redis = get_redis()
    pipe = redis.pipeline()
    pipe.incr(key)
    pipe.expire(key, window, nx=True)
    count, _ = await pipe.execute()
    return count <= limit
