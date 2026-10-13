"""Password hashing (argon2) and JWT access/refresh tokens."""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

from app.core.config import get_settings

_hasher = PasswordHasher()

ACCESS = "access"
REFRESH = "refresh"


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return _hasher.verify(password_hash, password)
    except VerifyMismatchError:
        return False
    except Exception:  # noqa: BLE001 - malformed hash etc. -> treat as mismatch
        return False


# A real argon2 hash to verify against when the user doesn't exist, so the
# unknown-user and wrong-password login paths take the same time (no timing
# enumeration).
_DUMMY_HASH = _hasher.hash("dummy-password-for-constant-time")


def dummy_verify(password: str) -> None:
    """Burn the same time as a real verify; result is discarded."""
    try:
        _hasher.verify(_DUMMY_HASH, password)
    except Exception:  # noqa: BLE001
        pass


def _create_token(sub: str, token_type: str, ttl: timedelta) -> str:
    s = get_settings()
    now = datetime.now(timezone.utc)
    payload: dict[str, Any] = {
        "sub": sub,
        "type": token_type,
        "iat": int(now.timestamp()),
        "exp": int((now + ttl).timestamp()),
        "jti": uuid.uuid4().hex,
    }
    return jwt.encode(payload, s.jwt_secret, algorithm=s.jwt_algorithm)


def create_access_token(sub: str) -> str:
    s = get_settings()
    return _create_token(sub, ACCESS, timedelta(minutes=s.access_token_ttl_min))


def create_refresh_token(sub: str) -> str:
    s = get_settings()
    return _create_token(sub, REFRESH, timedelta(days=s.refresh_token_ttl_days))


def decode_token(token: str, expected_type: str | None = None) -> dict[str, Any]:
    """Decode and validate a JWT; raises ``jwt.PyJWTError`` on any problem.

    ``sub`` and ``exp`` are required, so callers can rely on ``payload["sub"]``
    being present without risking an uncaught ``KeyError``.
    """
    s = get_settings()
    payload = jwt.decode(
        token,
        s.jwt_secret,
        algorithms=[s.jwt_algorithm],
        options={"require": ["sub", "exp"]},
    )
    if expected_type is not None and payload.get("type") != expected_type:
        raise jwt.InvalidTokenError("Unexpected token type")
    return payload
